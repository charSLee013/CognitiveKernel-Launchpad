#
# 内置Playwright实现的WebEnv
# 替换HTTP API架构，直接使用Playwright Python API

import os
import time
import base64
import json
import uuid
import asyncio
import threading
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.sync_api import sync_playwright, Browser as SyncBrowser, BrowserContext as SyncBrowserContext, Page as SyncPage

from ..agents.utils import KwargsInitializable, rprint, zwarn, zlog
from .utils import WebState, MyMarkdownify


class PlaywrightBrowserPool:
    """Playwright浏览器池管理器"""

    def __init__(self, max_browsers: int = 16, headless: bool = True, logger=None):
        self.max_browsers = max_browsers
        self.headless = headless
        self.logger = logger
        self.browsers: Dict[str, Dict] = {}
        self.playwright = None
        self.browser_type = None
        self._lock = threading.Lock()
        
    def start(self):
        """启动Playwright和浏览器池"""
        if self.playwright is None:
            # 简单直接的启动方式
            try:
                self.playwright = sync_playwright().start()
            except Exception as e:
                if self.logger:
                    self.logger.error("[PLAYWRIGHT_POOL] Failed to start Playwright: %s", e)
                raise RuntimeError(f"Cannot start Playwright: {e}")

            # 使用Chrome而不是Chromium，提供更好的兼容性
            self.browser_type = self.playwright.chromium  # Playwright中Chrome通过chromium接口访问

            if self.logger:
                self.logger.info("[PLAYWRIGHT_POOL] Started with max_browsers=%d (Chrome headless)", self.max_browsers)
    
    def stop(self):
        """停止所有浏览器和Playwright"""
        with self._lock:
            for browser_id, browser_info in self.browsers.items():
                try:
                    if browser_info.get('context'):
                        browser_info['context'].close()
                    if browser_info.get('browser'):
                        browser_info['browser'].close()
                except Exception as e:
                    if self.logger:
                        self.logger.warning("[PLAYWRIGHT_POOL] Error closing browser %s: %s", browser_id, e)

            self.browsers.clear()

            if self.playwright:
                self.playwright.stop()
                self.playwright = None

            if self.logger:
                self.logger.info("[PLAYWRIGHT_POOL] Stopped")
    
    def get_browser(self, storage_state=None, geo_location=None) -> str:
        """获取浏览器实例，返回browser_id"""
        with self._lock:
            # 检查是否有可用的浏览器槽位
            if len(self.browsers) >= self.max_browsers:
                # 清理不活跃的浏览器
                self._cleanup_inactive_browsers()
                
                if len(self.browsers) >= self.max_browsers:
                    raise RuntimeError(f"Browser pool exhausted (max: {self.max_browsers})")
            
            browser_id = str(uuid.uuid4())
            
            try:
                # 启动新浏览器 - 使用Chrome headless模式
                launch_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]

                # Docker环境不再需要特殊参数 - 移除不必要的环境变量检查
                # launch_args.extend([
                #     '--disable-dev-shm-usage',
                #     '--no-first-run',
                #     '--no-default-browser-check'
                # ])

                # 尝试使用Chrome，如果失败则回退到Chromium
                try:
                    browser = self.browser_type.launch(
                        headless=self.headless,
                        args=launch_args,
                        channel="chrome"  # 明确指定使用Chrome
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning("[PLAYWRIGHT_POOL] Chrome not available, falling back to Chromium: %s", e)
                    browser = self.browser_type.launch(
                        headless=self.headless,
                        args=launch_args
                    )
                
                # 创建浏览器上下文 - 使用真实Chrome用户代理
                context_options = {
                    'viewport': {'width': 1024, 'height': 768},
                    'locale': 'en-US',
                    'geolocation': geo_location or {'latitude': 40.4415, 'longitude': -80.0125},
                    'permissions': ['geolocation'],
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'extra_http_headers': {
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
                    }
                }
                
                if storage_state:
                    context_options['storage_state'] = storage_state
                
                context = browser.new_context(**context_options)
                
                self.browsers[browser_id] = {
                    'browser': browser,
                    'context': context,
                    'pages': {},
                    'last_activity': time.time(),
                    'status': 'active'
                }
                
                if self.logger:
                    self.logger.info("[PLAYWRIGHT_POOL] Created browser %s", browser_id)
                
                return browser_id
                
            except Exception as e:
                if self.logger:
                    self.logger.error("[PLAYWRIGHT_POOL] Failed to create browser: %s", e)
                raise
    
    def close_browser(self, browser_id: str):
        """关闭指定浏览器"""
        with self._lock:
            if browser_id in self.browsers:
                browser_info = self.browsers[browser_id]
                try:
                    if browser_info.get('context'):
                        browser_info['context'].close()
                    if browser_info.get('browser'):
                        browser_info['browser'].close()
                    
                    del self.browsers[browser_id]
                    
                    if self.logger:
                        self.logger.info("[PLAYWRIGHT_POOL] Closed browser %s", browser_id)
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning("[PLAYWRIGHT_POOL] Error closing browser %s: %s", browser_id, e)
    
    def get_browser_context(self, browser_id: str) -> Optional[SyncBrowserContext]:
        """获取浏览器上下文"""
        browser_info = self.browsers.get(browser_id)
        if browser_info:
            browser_info['last_activity'] = time.time()
            return browser_info.get('context')
        return None
    
    def _cleanup_inactive_browsers(self):
        """清理不活跃的浏览器"""
        current_time = time.time()
        inactive_threshold = 3600  # 1小时不活跃则清理
        
        inactive_browsers = []
        for browser_id, browser_info in self.browsers.items():
            if current_time - browser_info['last_activity'] > inactive_threshold:
                inactive_browsers.append(browser_id)
        
        for browser_id in inactive_browsers:
            self.close_browser(browser_id)
            if self.logger:
                self.logger.info("[PLAYWRIGHT_POOL] Cleaned up inactive browser %s", browser_id)

    def get_status(self):
        """获取浏览器池状态"""
        with self._lock:
            active_count = len([b for b in self.browsers.values() if b['status'] == 'active'])
            return {
                'active': active_count,
                'total': len(self.browsers),
                'available': self.max_browsers - len(self.browsers),
                'max_browsers': self.max_browsers
            }


class PlaywrightWebEnv(KwargsInitializable):
    """基于Playwright的内置WebEnv实现"""

    def __init__(self, settings=None, starting=True, starting_target_url=None, logger=None, **kwargs):
        # 基础配置 - 从TOML配置读取
        if settings and hasattr(settings, 'web') and hasattr(settings.web, 'env_builtin'):
            self.max_browsers = settings.web.env_builtin.max_browsers
            self.headless = settings.web.env_builtin.headless
            self.web_timeout = settings.web.env_builtin.web_timeout
            self.screenshot_boxed = settings.web.env_builtin.screenshot_boxed
            self.target_url = settings.web.env_builtin.target_url
        else:
            # Fallback defaults if no settings provided
            self.max_browsers = 16
            self.headless = True
            self.web_timeout = 600
            self.screenshot_boxed = True
            self.target_url = "https://www.bing.com/"

        self.logger = logger

        # Playwright相关
        self.browser_pool = None
        self.current_browser_id = None
        self.current_page_id = None

        # 状态管理
        self.state: WebState = None

        super().__init__(**kwargs)

        # 创建浏览器池
        self._create_browser_pool()

        if starting:
            self.start(starting_target_url)
    
    def _create_browser_pool(self):
        """创建浏览器池"""
        self.browser_pool = PlaywrightBrowserPool(
            max_browsers=self.max_browsers,
            headless=self.headless,
            logger=self.logger
        )
        self.browser_pool.start()
    
    def start(self, target_url=None):
        """启动web环境"""
        self.stop()  # 先停止现有环境
        
        target_url = target_url if target_url is not None else self.target_url
        
        # Google到Bing的重定向（保持与原有逻辑一致）
        if 'www.google.com' in target_url and 'www.google.com/maps' not in target_url:
            target_url = target_url.replace('www.google.com', 'www.bing.com')
        
        self.init_state(target_url)
    
    def stop(self):
        """停止web环境"""
        if self.current_browser_id and self.browser_pool:
            self.browser_pool.close_browser(self.current_browser_id)
            self.current_browser_id = None
            self.current_page_id = None

        if self.state is not None:
            self.state = None

    def __del__(self):
        """析构函数"""
        self.stop()
        if self.browser_pool:
            self.browser_pool.stop()

    def get_state(self, export_to_dict=True, return_copy=True):
        """获取当前状态"""
        assert self.state is not None, "Current state is None, should first start it!"
        if export_to_dict:
            ret = self.state.to_dict()
        elif return_copy:
            ret = self.state.copy()
        else:
            ret = self.state
        return ret

    def get_target_url(self):
        """获取目标URL"""
        return self.target_url

    def init_state(self, target_url: str):
        """初始化浏览器状态"""
        if self.logger:
            self.logger.info("[PLAYWRIGHT_INIT] Starting browser initialization")
            self.logger.info("[PLAYWRIGHT_INIT] Target_URL: %s", target_url)

        # 获取浏览器实例
        self.current_browser_id = self.browser_pool.get_browser()

        if self.logger:
            self.logger.info("[PLAYWRIGHT_INIT] Browser_Created: %s", self.current_browser_id)

        # 打开页面
        self.current_page_id = self._open_page(target_url)

        if self.logger:
            self.logger.info("[PLAYWRIGHT_INIT] Page_Opened: %s", self.current_page_id)

        # 创建状态对象
        curr_step = 0
        self.state = WebState(
            browser_id=self.current_browser_id,
            page_id=self.current_page_id,
            target_url=target_url,
            curr_step=curr_step,
            total_actual_step=curr_step
        )

        # 获取初始页面信息
        results = self._get_accessibility_tree_results()
        self.state.update(**results)

        if self.logger:
            actual_url = getattr(self.state, 'step_url', 'unknown')
            self.logger.info("[PLAYWRIGHT_INIT] State_Initialized: Actual_URL: %s", actual_url)
            if actual_url != target_url:
                self.logger.warning("[PLAYWRIGHT_INIT] URL_Mismatch: Expected: %s | Actual: %s", target_url, actual_url)

    def _open_page(self, target_url: str) -> str:
        """打开新页面"""
        context = self.browser_pool.get_browser_context(self.current_browser_id)
        if not context:
            raise RuntimeError(f"Browser context not found for {self.current_browser_id}")

        page = context.new_page()
        page_id = str(uuid.uuid4())

        # 设置下载处理
        page.on("download", self._handle_download)

        # 导航到目标URL
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            # 存储页面引用
            browser_info = self.browser_pool.browsers[self.current_browser_id]
            browser_info['pages'][page_id] = page

            if self.logger:
                actual_url = page.url
                self.logger.info("[PLAYWRIGHT_PAGE] Opened: %s -> %s", target_url, actual_url)

            return page_id

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_PAGE] Failed to open %s: %s", target_url, e)
            raise

    def _handle_download(self, download):
        """处理文件下载"""
        try:
            # 生成下载文件路径
            download_path = f"./downloads/{download.suggested_filename}"
            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            # 保存文件
            download.save_as(download_path)

            # 更新状态中的下载文件列表
            if self.state and hasattr(self.state, 'downloaded_file_path'):
                if download_path not in self.state.downloaded_file_path:
                    self.state.downloaded_file_path.append(download_path)

            if self.logger:
                self.logger.info("[PLAYWRIGHT_DOWNLOAD] Saved: %s", download_path)

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_DOWNLOAD] Failed: %s", e)

    def _get_current_page(self) -> Optional[SyncPage]:
        """获取当前页面对象"""
        if not self.current_browser_id or not self.current_page_id:
            return None

        browser_info = self.browser_pool.browsers.get(self.current_browser_id)
        if not browser_info:
            return None

        return browser_info['pages'].get(self.current_page_id)

    def _get_accessibility_tree_results(self) -> Dict[str, Any]:
        """获取可访问性树和页面信息"""
        page = self._get_current_page()
        if not page:
            return self._get_default_results()

        try:
            # 获取基本页面信息
            current_url = page.url
            html_content = page.content()

            # 处理HTML为Markdown
            html_md = self._process_html(html_content)

            # 获取可访问性树
            accessibility_tree = self._get_accessibility_tree(page)

            # 获取截图
            screenshot_b64 = self._take_screenshot(page)

            # 检查Cookie弹窗
            has_cookie_popup = self._check_cookie_popup(page)

            results = {
                "current_accessibility_tree": accessibility_tree,
                "step_url": current_url,
                "html_md": html_md,
                "snapshot": "",  # 可以添加accessibility snapshot
                "boxed_screenshot": screenshot_b64,
                "downloaded_file_path": getattr(self.state, 'downloaded_file_path', []),
                "get_accessibility_tree_succeed": True,
                "current_has_cookie_popup": has_cookie_popup,
                "expanded_part": None
            }

            return results

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_AXTREE] Failed to get page info: %s", e)
            return self._get_default_results()

    def _get_default_results(self) -> Dict[str, Any]:
        """获取默认结果（错误情况下）"""
        return {
            "current_accessibility_tree": "**Warning**: The accessibility tree is currently unavailable.",
            "step_url": "",
            "html_md": "",
            "snapshot": "",
            "boxed_screenshot": "",
            "downloaded_file_path": [],
            "get_accessibility_tree_succeed": False,
            "current_has_cookie_popup": False,
            "expanded_part": None
        }

    def _process_html(self, html_content: str) -> str:
        """处理HTML内容为Markdown"""
        if not html_content.strip():
            return ""
        try:
            return MyMarkdownify.md_convert(html_content)
        except Exception as e:
            if self.logger:
                self.logger.warning("[PLAYWRIGHT_HTML] Failed to convert HTML: %s", e)
            return ""

    def _get_accessibility_tree(self, page: SyncPage) -> str:
        """获取可访问性树"""
        try:
            # 使用Playwright的accessibility API
            snapshot = page.accessibility.snapshot()
            if snapshot:
                return self._format_accessibility_tree(snapshot)
            else:
                return "No accessibility tree available"
        except Exception as e:
            if self.logger:
                self.logger.warning("[PLAYWRIGHT_AXTREE] Failed to get accessibility tree: %s", e)
            return "**Warning**: Failed to get accessibility tree"

    def _format_accessibility_tree(self, snapshot: Dict, level: int = 0) -> str:
        """格式化可访问性树为文本"""
        lines = []
        indent = "  " * level

        # 获取节点信息
        role = snapshot.get('role', 'unknown')
        name = snapshot.get('name', '')
        value = snapshot.get('value', '')

        # 构建节点描述
        node_desc = f"{indent}[{level}] {role}"
        if name:
            node_desc += f" \"{name}\""
        if value:
            node_desc += f" value=\"{value}\""

        lines.append(node_desc)

        # 递归处理子节点
        children = snapshot.get('children', [])
        for child in children:
            lines.extend(self._format_accessibility_tree(child, level + 1).split('\n'))

        return '\n'.join(lines)

    def _take_screenshot(self, page: SyncPage) -> str:
        """截取页面截图并返回base64编码"""
        try:
            screenshot_bytes = page.screenshot(full_page=False)
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            if self.logger:
                self.logger.warning("[PLAYWRIGHT_SCREENSHOT] Failed: %s", e)
            return ""

    def _check_cookie_popup(self, page: SyncPage) -> bool:
        """检查是否有Cookie弹窗"""
        try:
            # 常见的Cookie弹窗选择器
            cookie_selectors = [
                '[id*="cookie"]',
                '[class*="cookie"]',
                '[id*="consent"]',
                '[class*="consent"]',
                'button:has-text("Accept")',
                'button:has-text("Allow")',
                'button:has-text("Agree")'
            ]

            for selector in cookie_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    return True

            return False
        except Exception as e:
            if self.logger:
                self.logger.warning("[PLAYWRIGHT_COOKIE] Cookie popup check failed: %s", e)
            return False

    def step_state(self, action_string: str) -> str:
        """执行浏览器动作"""
        if self.logger:
            self.logger.info("[PLAYWRIGHT_ACTION] Step_State_Start: %s", action_string)

        # 解析动作
        action = self._parse_action(action_string)

        # 更新状态
        self.state.curr_step += 1
        self.state.total_actual_step += 1
        self.state.update(action=action, action_string=action_string, error_message="")

        # 执行动作
        if not action["action_name"]:
            error_msg = f"The action you previously choose is not well-formatted: {action_string}"
            self.state.error_message = error_msg
            return error_msg

        try:
            success = self._perform_action(action)

            if not success:
                error_msg = f"The action you have chosen cannot be executed: {action_string}"
                self.state.error_message = error_msg
                if self.logger:
                    self.logger.error("[PLAYWRIGHT_ACTION] Failed: %s", action_string)
                return error_msg
            else:
                # 获取新状态
                if self.logger:
                    self.logger.info("[PLAYWRIGHT_ACTION] Success: %s", action_string)

                results = self._get_accessibility_tree_results()
                self.state.update(**results)
                return f"Browser step: {action_string}"

        except Exception as e:
            error_msg = f"Browser error: {e}"
            self.state.error_message = error_msg
            if self.logger:
                self.logger.error("[PLAYWRIGHT_ACTION] Exception: %s", e)
            return error_msg

    def _parse_action(self, action_string: str) -> Dict[str, Any]:
        """解析动作字符串"""
        action = {
            "action_name": "",
            "target_id": None,
            "target_element_type": "",
            "target_element_name": "",
            "action_value": "",
            "need_enter": True
        }

        action_string = action_string.strip()

        # 解析不同类型的动作
        if action_string.startswith("click"):
            action["action_name"] = "click"
            # 解析 click [id] name 格式
            import re
            match = re.match(r'click\s+\[(\d+)\]\s*(.*)', action_string)
            if match:
                action["target_id"] = int(match.group(1))
                action["target_element_name"] = match.group(2).strip()
                action["target_element_type"] = "clickable"

        elif action_string.startswith("type"):
            action["action_name"] = "type"
            # 解析 type [id] content 格式
            import re
            match = re.match(r'type\s+\[(\d+)\]\s+(.*?)(?:\[NOENTER\])?$', action_string)
            if match:
                action["target_id"] = int(match.group(1))
                action["action_value"] = match.group(2).strip()
                action["target_element_type"] = "textbox"
                action["need_enter"] = "[NOENTER]" not in action_string

        elif action_string in ["scroll_up", "scroll up"]:
            action["action_name"] = "scroll_up"

        elif action_string in ["scroll_down", "scroll down"]:
            action["action_name"] = "scroll_down"

        elif action_string == "wait":
            action["action_name"] = "wait"

        elif action_string == "goback":
            action["action_name"] = "goback"

        elif action_string == "restart":
            action["action_name"] = "restart"

        elif action_string.startswith("goto"):
            action["action_name"] = "goto"
            # 解析 goto url 格式
            parts = action_string.split(None, 1)
            if len(parts) > 1:
                action["action_value"] = parts[1].strip()

        elif action_string.startswith("stop"):
            action["action_name"] = "stop"

        elif action_string.startswith("save"):
            action["action_name"] = "save"

        elif action_string.startswith("screenshot"):
            action["action_name"] = "screenshot"
            parts = action_string.split()
            if len(parts) > 1:
                action["action_value"] = " ".join(parts[1:])

        return action

    def _perform_action(self, action: Dict[str, Any]) -> bool:
        """执行具体的浏览器动作"""
        page = self._get_current_page()
        if not page:
            return False

        action_name = action["action_name"]

        try:
            if action_name == "click":
                return self._perform_click(page, action)

            elif action_name == "type":
                return self._perform_type(page, action)

            elif action_name == "scroll_up":
                page.keyboard.press("PageUp")
                return True

            elif action_name == "scroll_down":
                page.keyboard.press("PageDown")
                return True

            elif action_name == "wait":
                time.sleep(5)
                return True

            elif action_name == "goback":
                page.go_back(wait_until="domcontentloaded")
                return True

            elif action_name == "restart":
                page.goto(self.target_url, wait_until="domcontentloaded")
                return True

            elif action_name == "goto":
                url = action.get("action_value", "")
                if url:
                    page.goto(url, wait_until="domcontentloaded")
                    return True
                return False

            elif action_name in ["stop", "save", "screenshot"]:
                # 这些动作由上层处理
                return True

            else:
                if self.logger:
                    self.logger.warning("[PLAYWRIGHT_ACTION] Unknown action: %s", action_name)
                return False

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_ACTION] Error executing %s: %s", action_name, e)
            return False

    def _perform_click(self, page: SyncPage, action: Dict[str, Any]) -> bool:
        """执行点击动作"""
        target_id = action.get("target_id")
        if target_id is None:
            return False

        try:
            # 使用简化的选择器策略
            # 在实际实现中，需要维护元素ID到选择器的映射
            # 这里使用一个简化的实现

            # 尝试通过data-testid或其他属性查找元素
            selectors = [
                f'[data-testid="{target_id}"]',
                f'[data-id="{target_id}"]',
                f'#{target_id}',
                f'*:nth-child({target_id})'
            ]

            element = None
            for selector in selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        break
                except:
                    continue

            if element:
                element.click()
                return True
            else:
                # 如果找不到特定元素，尝试通过可访问性树查找
                return self._click_by_accessibility_tree(page, target_id)

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_CLICK] Error: %s", e)
            return False

    def _perform_type(self, page: SyncPage, action: Dict[str, Any]) -> bool:
        """执行输入动作"""
        target_id = action.get("target_id")
        text = action.get("action_value", "")
        need_enter = action.get("need_enter", True)

        if target_id is None:
            return False

        try:
            # 类似点击，查找输入元素
            selectors = [
                f'[data-testid="{target_id}"]',
                f'[data-id="{target_id}"]',
                f'#{target_id}',
                'input[type="text"]',
                'input[type="search"]',
                'textarea'
            ]

            element = None
            for selector in selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        break
                except:
                    continue

            if element:
                element.click()  # 先点击获得焦点
                element.clear()  # 清空现有内容
                element.type(text)  # 输入文本

                if need_enter:
                    element.press("Enter")

                return True
            else:
                return self._type_by_accessibility_tree(page, target_id, text, need_enter)

        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_TYPE] Error: %s", e)
            return False

    def _click_by_accessibility_tree(self, page: SyncPage, target_id: int) -> bool:
        """通过可访问性树查找并点击元素"""
        try:
            # 获取所有可点击元素
            clickable_elements = page.query_selector_all('button, a, [role="button"], [onclick], input[type="submit"], input[type="button"]')

            if target_id < len(clickable_elements):
                clickable_elements[target_id].click()
                return True

            return False
        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_CLICK_AX] Error: %s", e)
            return False

    def _type_by_accessibility_tree(self, page: SyncPage, target_id: int, text: str, need_enter: bool) -> bool:
        """通过可访问性树查找并输入文本"""
        try:
            # 获取所有输入元素
            input_elements = page.query_selector_all('input[type="text"], input[type="search"], input[type="email"], input[type="password"], textarea')

            if target_id < len(input_elements):
                element = input_elements[target_id]
                element.click()
                element.clear()
                element.type(text)

                if need_enter:
                    element.press("Enter")

                return True

            return False
        except Exception as e:
            if self.logger:
                self.logger.error("[PLAYWRIGHT_TYPE_AX] Error: %s", e)
            return False

    def sync_files(self):
        """同步下载的文件（内置实现中文件已经直接保存到本地）"""
        # 在内置实现中，文件下载已经通过_handle_download直接处理
        # 这里只需要确保状态中的文件路径是正确的
        if self.logger:
            downloaded_files = getattr(self.state, 'downloaded_file_path', [])
            self.logger.info("[PLAYWRIGHT_SYNC] Downloaded files: %s", downloaded_files)
        return True
