#

# the agent

__all__ = [
    "register_template", "get_template",
    "AgentResult", "ActionResult", "MultiStepAgent"
]

import json
import traceback
import time
from typing import List
from collections import Counter
from .model import LLM
from .session import AgentSession
from .tool import Tool
from .utils import KwargsInitializable, rprint, TemplatedString, parse_response, CodeExecutor, zwarn

TEMPLATES = {}

def register_template(templates):
    for k, v in templates.items():
        # assert k not in TEMPLATES
        if k in TEMPLATES and v != TEMPLATES[k]:
            zwarn(f"Overwrite previous templates for k={k}")
        TEMPLATES[k] = v

def get_template(key: str):
    return TemplatedString(TEMPLATES.get(key))

# --
# storage of the results for an agent call
class AgentResult(KwargsInitializable):
    def __init__(self, **kwargs):
        self.output = ""  # formatted output
        self.log = ""  # other outputs
        self.task = ""  # target task
        self.repr = None  # explicit repr?
        super().__init__(_assert_existing=False, **kwargs)

    def to_dict(self):
        return self.__dict__.copy()

    def __contains__(self, item):
        return item in self.__dict__

    def __getitem__(self, item):  # look like a dict
        return self.__dict__[item]

    def __repr__(self):
        if self.repr:  # if directly specified
            return self.repr
        ret = self.output if self.output else "N/A"
        if self.log:
            ret = f"{ret} ({self.log})"
        return ret

class ActionResult(KwargsInitializable):
    def __init__(self, action: str, result: str = None, **kwargs):
        self.action = action
        self.result = result
        super().__init__(_assert_existing=False, **kwargs)

    def __repr__(self):
        return f"Action={self.action}, Result={self.result}"

# --
class StopReasons:
    NORMAL_END = "Normal Ending."
    MAX_STEP = "Max step exceeded."
    MAX_TIME = "Time limit exceeded."

CODE_ERROR_PERFIX = "Code Execution Error:\n"

# --
# a basic class for a multi-step agent
class MultiStepAgent(KwargsInitializable):
    def __init__(self, logger=None, **kwargs):
        self.name = ""
        self.description = ""
        # self.sub_agents: List[MultiStepAgent] = []  # sub-agents (sth like advanced tools)
        self.sub_agent_names = []  # sub-agent names (able to be found using getattr!)
        self.tools: List[Tool] = []  # tools
        self.model = LLM(_default_init=True)  # main loop's model
        self.logger = logger  # 诊断日志器
        self.templates = {}  # template names: plan/action/end
        self.max_steps = 10  # maximum steps
        self.max_time_limit = 0  # early stop if exceeding this time (in seconds)
        self.recent_steps = 5  # feed recent steps
        self.store_io = True  # whether store the inputs/outputs of the model in session
        self.exec_timeout_with_call = 0  # how many seconds to timeout for each exec (0 means no timeout) (with sub-agent call)
        self.exec_timeout_wo_call = 0  # how many seconds to timeout for each exec (0 means no timeout) (without sub-agent call)
        self.obs_max_token = 8192  # avoid obs that is too long
        # --
        self.active_functions = []  # note: put active functions here!
        # --
        super().__init__(**kwargs)
        self.templates = {k: get_template(v) for k, v in self.templates.items()}  # read real templates from registered ones
        # self.python_executor = CodeExecutor()  # our own simple python executor (simply recreate it for each run!)
        ALL_FUNCTIONS = {z.name: z for z in (self.sub_agents + self.tools)}
        assert len(ALL_FUNCTIONS) == len(self.sub_agents + self.tools), "There may be repeated function names of sub-agents and tools."
        self.ACTIVE_FUNCTIONS = {k: ALL_FUNCTIONS[k] for k in self.active_functions}
        self.final_result = None  # to store final result
        # --
        # repeat-output tracking for minimal prompt nudging
        self._last_observation_text = None
        self._repeat_count = 0
        self._repeat_warning_msg = ""

    @property
    def sub_agents(self):  # obtaining the sub-agents by getattr
        return [getattr(self, name) for name in self.sub_agent_names]

    # Training/evaluation methods removed - not needed for simple query processing
    # get_call_stat(), get_seed(), set_seed() removed as per simplification goals

    # called as a managed agent
    # note: the communications/APIs between agents should be simple: INPUT={task, **kwargs}, OUTPUT={output(None if error), log}
    def __call__(self, task: str, **kwargs):
        # task = f"Complete the following task:\n{input_prompt}\n(* Your final answer should follow the format: {output_format})"  # note: no longer format it here!
        session = self.run(task, **kwargs)  # run the process
        final_results = session.get_current_step().get("end", {}).get("final_results", {})
        ret = AgentResult(task=task, session=session, **final_results)  # a simple wrapper
        return ret

    def get_function_definition(self, short: bool):
        raise NotImplementedError("To be implemented")

    # run as the main agent
    def run(self, task, stream=False, session=None, max_steps: int = None, **extra_info):
        start_pc = time.perf_counter()
        # Initialize session
        if session is None:
            session = AgentSession(task=task, **extra_info)

        max_steps = max_steps if max_steps is not None else self.max_steps

        # --
        if stream:  # The steps are returned as they are executed through a generator to iterate on.
            ret = self.yield_session_run(session=session, max_steps=max_steps)  # return a yielder
        else:  # Outputs are returned only at the end. We only look at the last step.
            for step_info in self.yield_session_run(session=session, max_steps=max_steps):
                pass
            ret = session

        execution_time = time.perf_counter() - start_pc
        rprint(f"ZZEnd task for {self.name} [ctime={time.ctime()}, interval={execution_time}]")
        return ret

    # main running loop
    def yield_session_run(self, session, max_steps):
        # run them!
        start_pc = time.perf_counter()
        # reset repeat-tracking per run
        self._last_observation_text = None
        self._repeat_count = 0
        self._repeat_warning_msg = ""

        self.init_run(session)  # start

        progress_state = {}  # current state
        stop_reason = None
        while True:
            step_idx = session.num_of_steps()
            _error_counts = sum(self.get_obs_str(z['action']).strip().startswith(CODE_ERROR_PERFIX) for z in session.steps)
            elapsed_time = time.perf_counter() - start_pc
            # 埋点：打印每步的限制检查
            print(f"[yield_session_run] Step {step_idx}: error_counts={_error_counts}, elapsed={elapsed_time:.1f}s")
            print(f"[yield_session_run] Limits: max_steps={max_steps}, max_time_limit={self.max_time_limit}")
            if (step_idx >= max_steps + _error_counts) or (step_idx >= int(max_steps*1.5)):  # make up for the errors (but avoid too many steps)
                print(f"[yield_session_run] STOP: MAX_STEP reached (step_idx={step_idx}, limit={max_steps + _error_counts} or {int(max_steps*1.5)})")
                stop_reason = StopReasons.MAX_STEP  # step limit
                break
            if (self.max_time_limit > 0) and (elapsed_time > self.max_time_limit):
                print(f"[yield_session_run] STOP: MAX_TIME reached (elapsed={elapsed_time:.1f}s, limit={self.max_time_limit}s)")
                stop_reason = StopReasons.MAX_TIME  # time limit
                break
            rprint(f"# ======\nAgent {self.name} -- Step {step_idx}", timed=True)
            _step_info = {"step_idx": step_idx}
            session.add_step(_step_info)  # simply append before running
            yield from self.step(session, progress_state)
            if self.step_check_end(session):
                stop_reason = StopReasons.NORMAL_END
                break
        rprint(f"# ======\nAgent {self.name} -- Stop reason={stop_reason}", timed=True)
        yield from self.finalize(session, progress_state, stop_reason)  # ending!
        self.end_run(session)
        # --

    def step(self, session, state):
        _input_kwargs, _extra_kwargs = self.step_prepare(session, state)
        _current_step = session.get_current_step()
        # planning
        has_plan_template = "plan" in self.templates
        if has_plan_template:  # planning to update state
            plan_messages = self.templates["plan"].format(**_input_kwargs)
            # 埋点：LLM 规划调用
            if hasattr(self, 'logger') and self.logger:
                self.logger.info("[WEB_LLM_PLAN] Task: %s", session.task[:200] + "..." if len(session.task) > 200 else session.task)
            plan_response = self.step_call(messages=plan_messages, session=session)
            plan_res = self._parse_output(plan_response)
            # 埋点：LLM 规划结果
            if hasattr(self, 'logger') and self.logger:
                self.logger.info("[WEB_LLM_PLAN] Response: %s", plan_response[:500] + "..." if len(plan_response) > 500 else plan_response)
                self.logger.info("[WEB_LLM_PLAN] Parsed: %s", plan_res)
            # state update
            if plan_res["code"]:
                try:
                    new_state = eval(plan_res["code"])  # directly eval
                except:
                    new_state = None
                if new_state:  # note: inplace update!
                    state.clear()
                    state.update(new_state)
                else:
                    zwarn("State NOT changed due to empty output!")
            else:
                # if jailbreak detected, change the experience state by fource.
                if plan_res['thought'] == 'Jailbreak or content filter violation detected. Please modify your prompt or stop with N/A.':
                    if 'experience' in state:
                        state['experience'].append(f'Jailbreak or content filter violation detected for the action {_input_kwargs["recent_steps_str"].split("Action:")[1]}. Please modify your prompt or stop with N/A.')
                    else:
                        state['experience'] = []
                    # hardcode here: disable the current visual_content if jailbreaking. This is because most jailbreak happens for images.
                    _input_kwargs['visual_content'] = None
            # update session step
            _current_step["plan"] = plan_res
            plan_res["state"] = state.copy()  # after updating the progress state (make a copy)
            if self.store_io:  # further storage
                plan_res.update({"llm_input": plan_messages, "llm_output": plan_response})
            yield {"type": "plan", "step_info": _current_step}
        # predict action
        _action_input_kwargs = _input_kwargs.copy()
        _action_input_kwargs["state"] = json.dumps(state, ensure_ascii=False, indent=2)  # there can be state updates
        action_messages = self.templates["action"].format(**_action_input_kwargs)
        # Inject minimal repeat-warning hint for NEXT step if previous outputs repeated
        if getattr(self, "_repeat_warning_msg", ""):
            if isinstance(action_messages, list):
                action_messages = list(action_messages)
                action_messages.append({"role": "user", "content": self._repeat_warning_msg})
        # 埋点：LLM 动作调用
        if hasattr(self, 'logger') and self.logger:
            current_url = "unknown"
            if "web_page" in _action_input_kwargs:
                # 尝试从 accessibility tree 中提取 URL
                web_page = _action_input_kwargs["web_page"]
                if "RootWebArea" in web_page:
                    lines = web_page.split('\n')
                    for line in lines:
                        if "RootWebArea" in line and "'" in line:
                            current_url = line.split("'")[1] if "'" in line else "unknown"
                            break
            self.logger.info("[WEB_LLM_ACTION] Browser_State: %s", current_url)
        action_response = self.step_call(messages=action_messages, session=session)
        action_res = self._parse_output(action_response)
        # 埋点：LLM 动作结果
        if hasattr(self, 'logger') and self.logger:
            self.logger.info("[WEB_LLM_ACTION] Response: %s", action_response[:500] + "..." if len(action_response) > 500 else action_response)
            self.logger.info("[WEB_LLM_ACTION] Actions: %s", action_res.get('code', 'No code generated'))
        # perform action
        step_res = self.step_action(action_res, _action_input_kwargs, **_extra_kwargs)
        # update session info
        _current_step["action"] = action_res
        action_res["observation"] = step_res  # after executing the step
        # update repeat-tracking for next step
        _obs_txt = self._normalize_observation(step_res)
        if _obs_txt and _obs_txt == self._last_observation_text:
            self._repeat_count += 1
        else:
            self._repeat_count = 0
        self._last_observation_text = _obs_txt
        if self._repeat_count > 0 and _obs_txt:
            self._repeat_warning_msg = (
                f"Notice: The last step produced the exact same output as before (repeated {self._repeat_count + 1} times): {_obs_txt}\n"
                "If the task is complete, call stop(output=<YOUR_FINAL_ANSWER>, log='...') NOW to finalize.\n"
                "Otherwise, investigate why the result repeated (e.g., state not updated, code had no effect) BEFORE continuing.\n"
                "Good cases:\n"
                "- stop(output=<YOUR_FINAL_ANSWER>, log='Answer verified; finalizing')\n"
                "- Update progress state (e.g., add a completed note) and produce a DIFFERENT next action.\n"
                "Bad cases:\n"
                "- Printing the same output again without any change.\n"
                "- Continuing without calling stop when the result is already final."
            )
        else:
            self._repeat_warning_msg = ""
        if self.store_io:  # further storage
            action_res.update({"llm_input": action_messages, "llm_output": action_response})
        yield {"type": "action", "step_info": _current_step}
        # --

    def finalize(self, session, state, stop_reason: str):
        has_end_template = "end" in self.templates
        has_final_result = self.has_final_result()
        final_results = self.get_final_result() if has_final_result else None
        if has_end_template:  # we have an ending module to further specify final results
            _input_kwargs, _extra_kwargs = self.step_prepare(session, state)
            # --
            # special ask_llm if not normal ending
            if stop_reason != StopReasons.NORMAL_END and hasattr(self, "tool_ask_llm"):
                ask_llm_output = self.tool_ask_llm(session.task)  # directly ask it
                _input_kwargs["ask_llm_output"] = ask_llm_output
            # --
            if final_results:
                stop_reason = f"{stop_reason} (with the result of {final_results})"
            _input_kwargs["stop_reason"] = stop_reason
            end_messages = self.templates["end"].format(**_input_kwargs)
            end_response = self.step_call(messages=end_messages, session=session)
            end_res = self._parse_output(end_response)
            if self.store_io:  # further storage
                end_res.update({"llm_input": end_messages, "llm_output": end_response})
        else:  # no end module
            end_res = {}
        # no need to execute anything and simply prepare final outputs
        _current_step = session.get_current_step()
        if has_end_template or final_results is None:  # try to get final results, end_module can override final_results
            try:
                final_results = eval(end_res["code"])
                assert isinstance(final_results, dict) and "output" in final_results and "log" in final_results
            except Exception as e:  # use the final step's observation as the result!
                # 埋点：finalizing step 错误详情
                if hasattr(self, 'logger') and self.logger:
                    self.logger.error("[WEB_FINALIZING_ERROR] Function: finalize | Line: 302")
                    self.logger.error("[WEB_FINALIZING_ERROR] Error: %s", str(e))
                    self.logger.error("[WEB_FINALIZING_ERROR] End_Response: %s", end_response if 'end_response' in locals() else "No end_response")
                    self.logger.error("[WEB_FINALIZING_ERROR] End_Code: %s", end_res.get("code", "No code in end_res"))
                    self.logger.error("[WEB_FINALIZING_ERROR] Stop_Reason: %s", stop_reason if 'stop_reason' in locals() else "Unknown")
                _log = "We are returning the final step's answer since there are some problems in the finalizing step." if has_end_template else ""
                final_results = {"output": self.get_obs_str(_current_step), "log": _log}
        end_res["final_results"] = final_results
        # --
        _current_step["end"] = end_res
        yield {"type": "end", "step_info": _current_step}
        # --

    # --
    # other helpers

    def _normalize_observation(self, obs):
        if isinstance(obs, (list, tuple)):
            if not obs:
                return ""
            return str(obs[0]).strip()
        return str(obs).strip() if obs is not None else ""

    def get_obs_str(self, action, obs=None, add_seq_enum=True):
        if obs is None:
            obs = action.get("observation", "None")
        if isinstance(obs, (list, tuple)):  # list them
            ret = "\n".join([(f"- Result {ii}: {zz}" if add_seq_enum else str(zz)) for ii, zz in enumerate(obs)])
        else:
            ret = str(obs)
        # --
        if len(ret) > self.obs_max_token:
            ret = f"{ret[:self.obs_max_token]} ... (observation string truncated: exceeded {self.obs_max_token} characters)"
        return ret

    # common preparations of inputs
    def _prepare_common_input_kwargs(self, session, state):
        # previous steps
        _recent_steps = session.get_latest_steps(count=self.recent_steps)  # no including the last which is simply empty
        _recent_steps_str = "\n\n".join([f"### Step {ss['step_idx']}\nThought: {ss['action']['thought']}\nAction: ```\n{ss['action']['code']}```\nObservation: {self.get_obs_str(ss['action'])}" for ii, ss in enumerate(_recent_steps)])
        _current_step = session.get_current_step()
        _current_step_action = _current_step.get("action", {})
        _current_step_str = f"Thought: {_current_step_action.get('thought')}\nAction: ```\n{_current_step_action.get('code')}```\nObservation: {self.get_obs_str(_current_step_action)}"
        # tools and sub-agents
        ret = {
            "task": session.task, "state": json.dumps(state, ensure_ascii=False, indent=2),
            "recent_steps": _recent_steps, "recent_steps_str": _recent_steps_str,
            "current_step": _current_step, "current_step_str": _current_step_str,
        }
        for short in [True, False]:
            _subagent_str = "## Sub-Agent Functions\n" + "\n".join([z.get_function_definition(short) for z in self.sub_agents])
            _tool_str = "## Tool Functions\n" + "\n".join([z.get_function_definition(short) for z in self.tools])
            _subagent_tool_str = f"{_subagent_str}\n\n{_tool_str}"
            _kkk = "subagent_tool_str_short" if short else "subagent_tool_str_long"
            ret[_kkk] = _subagent_tool_str
        # --
        return ret

    def _parse_output(self, output: str):
        _target_list = ["Thought:", "Code:"]
        if (output is None) or (output.strip() == ""):
            output = "Thought: Model returns empty output. There might be a connection error or your input is too complex. Consider simplifying your query."  # error without any output
        _parsed_output = parse_response(output, _target_list, return_dict=True)
        _res = {k[:-1].lower(): _parsed_output[k] for k in _target_list}
        # parse code
        _res["code"] = CodeExecutor.extract_code(output)
        return _res

    # --
    # an explicit mechanism for ending
    def has_final_result(self):
        return self.final_result is not None

    def put_final_result(self, final_result):
        self.final_result = final_result

    def get_final_result(self, clear=True):
        ret = self.final_result
        if clear:
            self.final_result = None
        return ret
    # --

    # --
    # to be implemented in sub-classes

    def init_run(self, session):
        pass

    def end_run(self, session):
        pass

    def step_call(self, messages, session, model=None):
        if model is None:
            model = self.model
        response = model(messages)
        return response

    def step_prepare(self, session, state):
        _input_kwargs = self._prepare_common_input_kwargs(session, state)
        _extra_kwargs = {}
        return _input_kwargs, _extra_kwargs

    def step_action(self, action_res, action_input_kwargs, **kwargs):
        python_executor = CodeExecutor()
        python_executor.add_global_vars(**self.ACTIVE_FUNCTIONS)  # to avoid that things might get re-defined at some place ...
        _exec_timeout = self.exec_timeout_with_call if any((z in action_res["code"]) for z in self.sub_agent_names) else self.exec_timeout_wo_call  # choose timeout value
        python_executor.run(action_res["code"], catch_exception=True, timeout=_exec_timeout)  # handle err inside!
        ret = python_executor.get_print_results()  # currently return a list of printed results
        rprint(f"Obtain action res = {ret}", style="white on yellow")
        return ret  # return a result str

    def step_check_end(self, session):
        return self.has_final_result()
