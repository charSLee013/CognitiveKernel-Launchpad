#
import time
import re
import random

from ..agents.agent import MultiStepAgent, register_template, AgentResult
from ..agents.tool import StopTool, AskLLMTool, SimpleSearchTool
from ..agents.utils import zwarn, CodeExecutor, rprint
from ..ck_web.agent import WebAgent
# SmolWeb alternative removed
from ..ck_file.agent import FileAgent
from .prompts import PROMPTS as CK_PROMPTS

# --
class CKAgent(MultiStepAgent):
    def __init__(self, settings, logger=None, **kwargs):
        # note: this is a little tricky since things will get re-init again in super().__init__
        # Initialize search_backend attribute for KwargsInitializable
        self.search_backend = None
        # Dedicated single-thread executor for action code to ensure thread-affinity
        self._action_executor = None
        
        # Store settings reference
        self.settings = settings
        
        # sub-agents - pass settings to each sub-agent during construction
        self.web_agent = WebAgent(settings=settings, logger=logger, model=kwargs.get('model'))  # sub-agent for web
        self.file_agent = FileAgent(settings=settings)
        self.tool_ask_llm = AskLLMTool()

        # Configure search backend from config.toml if provided
        search_backend = kwargs.get('search_backend')
        if search_backend:
            try:
                from ..agents.search.config import SearchConfigManager
                SearchConfigManager.initialize_from_string(search_backend)
            except Exception as e:
                # LET IT CRASH - don't hide configuration errors
                raise RuntimeError(f"Failed to configure search backend {search_backend}: {e}") from e

        # Create search tool (will use configured backend or factory default)
        self.tool_simple_search = SimpleSearchTool()
        # Choose ck_end template by verbosity style (less|medium|more)
        style = kwargs.get('end_template', 'less')
        _end_map = {
            'less': 'ck_end_less',
            'medium': 'ck_end_medium',
            'more': 'ck_end_more',
        }
        end_tpl = _end_map.get(style, 'ck_end_less')

        feed_kwargs = dict(
            name="ck_agent",
            description="Cognitive Kernel, an initial autopilot system.",
            templates={"plan": "ck_plan", "action": "ck_action", "end": end_tpl},  # template names
            active_functions=["web_agent", "file_agent", "stop", "ask_llm", "simple_web_search"],  # enable the useful modules
            sub_agent_names=["web_agent", "file_agent"],  # note: another tricky point, use name rather than the objects themselves
            tools=[StopTool(agent=self), self.tool_ask_llm, self.tool_simple_search],  # add related tools
            max_steps=16,  # still give it more steps
            max_time_limit=4200,  # 70 minutes
            exec_timeout_with_call=1000,  # if calling sub-agent
            exec_timeout_wo_call=200,  # if not calling sub-agent
        )
        # Apply configuration overrides (remove internal-only keys first)
        if 'end_template' in kwargs:
            kwargs = {k: v for k, v in kwargs.items() if k != 'end_template'}
        feed_kwargs.update(kwargs)
        # Parallel processing removed - single execution path only
        # --
        register_template(CK_PROMPTS)  # add web prompts
        super().__init__(**feed_kwargs)
        self.tool_ask_llm.set_llm(self.model)  # another tricky part, we need to assign LLM later
        self.tool_simple_search.set_llm(self.model)
        # --

    def get_function_definition(self, short: bool):
        raise RuntimeError("Should NOT use CKAgent as a sub-agent!")

    def _ensure_action_executor(self):
        if self._action_executor is None:
            from concurrent.futures import ThreadPoolExecutor
            # Single dedicated worker thread to keep Playwright and sub-agents in one thread
            self._action_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ck_action")

    def step_action(self, action_res, action_input_kwargs, **kwargs):
        """Execute single action step in a dedicated thread (to avoid asyncio-loop conflicts)."""
        self._ensure_action_executor()

        def _do_execute():
            python_executor = CodeExecutor()
            python_executor.add_global_vars(**self.ACTIVE_FUNCTIONS)
            _exec_timeout = self.exec_timeout_with_call if any((z in action_res["code"]) for z in self.sub_agent_names) else self.exec_timeout_wo_call
            python_executor.run(action_res["code"], catch_exception=True, timeout=_exec_timeout)
            ret = python_executor.get_print_results()
            rprint(f"Obtain action res = {ret}", style="white on yellow")
            return ret

        # Run user action code on the dedicated worker thread and wait for completion
        future = self._action_executor.submit(_do_execute)
        return future.result()

    def end_run(self, session):
        ret = super().end_run(session)
        # Cleanly shutdown the dedicated action executor to release resources
        if self._action_executor is not None:
            self._action_executor.shutdown(wait=True)
            self._action_executor = None
        return ret
