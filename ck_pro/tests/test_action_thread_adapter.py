import threading
import os
import sys
import types

# Ensure package root is on path
sys.path.insert(0, os.path.abspath('.'))

# Provide lightweight stubs to avoid heavy deps during unit test
stub_web_agent_mod = types.ModuleType('ck_pro.ck_web.agent')
class _StubWebAgent:
    name = 'web_agent'
    def __init__(self, *args, **kwargs):
        pass
    def get_function_definition(self, short: bool):
        return 'web_agent(...)'
stub_web_agent_mod.WebAgent = _StubWebAgent
sys.modules['ck_pro.ck_web.agent'] = stub_web_agent_mod

stub_file_agent_mod = types.ModuleType('ck_pro.ck_file.agent')
class _StubFileAgent:
    name = 'file_agent'
    def __init__(self, *args, **kwargs):
        pass
    def get_function_definition(self, short: bool):
        return 'file_agent(...)'
stub_file_agent_mod.FileAgent = _StubFileAgent
sys.modules['ck_pro.ck_file.agent'] = stub_file_agent_mod

# Stub tools module to avoid importing bs4/requests in tests
stub_tools_mod = types.ModuleType('ck_pro.agents.tool')
class _StubTool:
    name = 'tool'
class _StubStopTool(_StubTool):
    name = 'stop'
    def __init__(self, *args, **kwargs):
        pass
class _StubAskLLMTool(_StubTool):
    name = 'ask_llm'
    def __init__(self, *args, **kwargs):
        pass
    def set_llm(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return 'ask_llm:stub'
class _StubSimpleSearchTool(_StubTool):
    name = 'simple_web_search'
    def __init__(self, *args, **kwargs):
        pass
    def set_llm(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return 'search:stub'
stub_tools_mod.Tool = _StubTool
stub_tools_mod.StopTool = _StubStopTool
stub_tools_mod.AskLLMTool = _StubAskLLMTool
stub_tools_mod.SimpleSearchTool = _StubSimpleSearchTool
sys.modules['ck_pro.agents.tool'] = stub_tools_mod

# Stub model to avoid tiktoken and external calls
stub_model_mod = types.ModuleType('ck_pro.agents.model')
class _StubLLM:
    def __init__(self, *_args, **_kwargs):
        pass
    def __call__(self, messages):
        # Minimal plausible response that passes parser: Thought + Code block
        return "Thought: test\nCode:\n```python\nprint('noop')\n```\n"
stub_model_mod.LLM = _StubLLM
sys.modules['ck_pro.agents.model'] = stub_model_mod

from ck_pro.ck_main.agent import CKAgent
from ck_pro.config.settings import Settings


def test_step_action_runs_in_dedicated_thread_and_is_consistent():
    # Create default settings for GAIA-removed configuration
    settings = Settings()
    agent = CKAgent(settings=settings)

    # Code that prints current thread name
    code_snippet = """
import threading
print(threading.current_thread().name)
"""
    action_res = {"code": code_snippet}

    # First run
    out1 = agent.step_action(action_res, {})
    tname1 = str(out1[0]).strip() if isinstance(out1, (list, tuple)) else str(out1).strip()

    # Second run (should use the same single worker thread)
    out2 = agent.step_action(action_res, {})
    tname2 = str(out2[0]).strip() if isinstance(out2, (list, tuple)) else str(out2).strip()

    # Should not be MainThread
    assert tname1 != "MainThread"
    assert tname2 != "MainThread"

    # Should be the same dedicated worker thread and prefixed as configured
    assert tname1 == tname2
    assert tname1.startswith("ck_action")

    # Cleanup
    agent.end_run(agent_session := type("S", (), {"id": "dummy"})())

