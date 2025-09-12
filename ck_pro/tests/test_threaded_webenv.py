import sys
import os
import types
import threading

# Ensure repo root on path
sys.path.insert(0, os.path.abspath('.'))

# Stub playwright modules to avoid dependency during import
sync_api = types.ModuleType('playwright.sync_api')
async_api = types.ModuleType('playwright.async_api')

# Minimal symbols referenced by imports
def _dummy():
    raise RuntimeError('should not be called in unit test')

sync_api.sync_playwright = lambda: types.SimpleNamespace(start=_dummy)
class _Dummy: ...
sync_api.Browser = _Dummy
sync_api.BrowserContext = _Dummy
sync_api.Page = _Dummy

async_api.async_playwright = _dummy
async_api.Browser = _Dummy
async_api.BrowserContext = _Dummy
async_api.Page = _Dummy

sys.modules['playwright.sync_api'] = sync_api
sys.modules['playwright.async_api'] = async_api

# Stub LLM to avoid heavy deps
stub_model_mod = types.ModuleType('ck_pro.agents.model')
class _StubLLM:
    def __init__(self, *_args, **_kwargs):
        pass
    def __call__(self, messages):
        return "ok"
stub_model_mod.LLM = _StubLLM
sys.modules['ck_pro.agents.model'] = stub_model_mod

# Import module under test after stubbing
import importlib

# Ensure previous test's stub of ck_pro.ck_web.agent is cleared
sys.modules.pop('ck_pro.ck_web.agent', None)

# Stub tools to avoid heavy deps
stub_tools_mod = types.ModuleType('ck_pro.agents.tool')
class _StubTool:
    name = 'tool'
class _StubSimpleSearchTool(_StubTool):
    name = 'simple_web_search'
    def __init__(self, *args, **kwargs):
        pass
    def set_llm(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return 'search:stub'
stub_tools_mod.SimpleSearchTool = _StubSimpleSearchTool
sys.modules['ck_pro.agents.tool'] = stub_tools_mod

plutils = importlib.import_module('ck_pro.ck_web.playwright_utils')

# Stub PlaywrightWebEnv to capture thread affinity and lifecycle
class _StubEnv:
    instances = []
    def __init__(self, **kwargs):
        self.created_thread = threading.current_thread().name
        self.calls = []
        self.stopped = False
        class _Pool:
            def __init__(self, outer):
                self.outer = outer
                self.stopped = False
            def stop(self):
                self.stopped = True
        self.browser_pool = _Pool(self)
        _StubEnv.instances.append(self)
    def get_state(self, export_to_dict=True, return_copy=True):
        self.calls.append(('get_state', threading.current_thread().name))
        return {
            'current_accessibility_tree': 'ok',
            'downloaded_file_path': [],
            'error_message': '',
            'current_has_cookie_popup': False,
            'html_md': ''
        }
    def step_state(self, action_string: str) -> str:
        self.calls.append(('step_state', threading.current_thread().name, action_string))
        return 'ok'
    def sync_files(self):
        self.calls.append(('sync_files', threading.current_thread().name))
        return True
    def stop(self):
        self.calls.append(('stop', threading.current_thread().name))
        self.stopped = True

plutils.PlaywrightWebEnv = _StubEnv

from ck_pro.ck_web.agent import WebAgent


def test_threaded_webenv_runs_all_calls_on_same_dedicated_thread_and_cleans_up():
    agent = WebAgent()
    # Force builtin path by making web_ip check fail (default will fail)
    session = type('S', (), {'id': 'sess1', 'info': {}})()

    agent.init_run(session)
    env = agent.web_envs[session.id]

    # Calls should execute on the dedicated thread, not MainThread
    state = env.get_state()
    assert state['current_accessibility_tree'] == 'ok'

    step_res = env.step_state('click [1]')
    assert step_res == 'ok'

    env.sync_files()

    # Verify underlying stub saw consistent thread usage
    stub = _StubEnv.instances[-1]
    created = stub.created_thread
    call_threads = [t for (_name, t, *_) in stub.calls if _name in ('get_state', 'step_state', 'sync_files')]

    assert created != 'MainThread'
    assert all(t == created for t in call_threads)

    # Ensure cleanup releases resources
    agent.end_run(session)
    assert stub.stopped is True
    assert stub.browser_pool.stopped is True

