#!/usr/bin/env python3
# NOTICE: This file is adapted from Tencent's CognitiveKernel-Pro (https://github.com/Tencent/CognitiveKernel-Pro).
# Modifications in this fork (2025) are for academic research and educational use only; no commercial use.
# Original rights belong to the original authors and Tencent; see upstream license for details.

"""
CognitiveKernel-Pro TOML Configuration System

Centralized, typed configuration management replacing JSON/dict passing.
Follows Linus Torvalds philosophy: simple, direct, no defensive backups.
"""

import os
import logging as std_logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """Language Model configuration - HTTP-only, fail-fast"""
    call_target: str  # Must be HTTP URL
    api_key: str      # Required
    model: str        # Required
    api_base_url: Optional[str] = None  # Backward compatibility
    request_timeout: int = 600
    max_retry_times: int = 5
    max_token_num: int = 20000
    extract_body: Dict[str, Any] = field(default_factory=dict)
    # Backward compatibility attributes (ignored)
    thinking: bool = False
    seed: int = 1377


@dataclass
class WebEnvConfig:
    """Web Environment configuration (HTTP API)"""
    web_ip: str = "localhost:3000"
    web_command: str = ""
    web_timeout: int = 600
    screenshot_boxed: bool = True
    target_url: str = "https://www.bing.com/"


@dataclass
class WebEnvBuiltinConfig:
    """Playwright builtin Web Environment configuration"""
    max_browsers: int = 16
    headless: bool = True
    web_timeout: int = 600
    screenshot_boxed: bool = True
    target_url: str = "https://www.bing.com/"


@dataclass
class WebAgentConfig:
    """Web Agent configuration"""
    max_steps: int = 20
    use_multimodal: str = "auto"  # off|yes|auto
    model: LLMConfig = field(default_factory=lambda: LLMConfig(
        call_target=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"),
        model=os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini"),
        extract_body={"temperature": 0.0, "max_tokens": 8192}
    ))
    model_multimodal: LLMConfig = field(default_factory=lambda: LLMConfig(
        call_target=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"),
        model=os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini"),
        extract_body={"temperature": 0.0, "max_tokens": 8192}
    ))
    env: WebEnvConfig = field(default_factory=WebEnvConfig)
    env_builtin: WebEnvBuiltinConfig = field(default_factory=WebEnvBuiltinConfig)


@dataclass
class FileAgentConfig:
    """File Agent configuration"""
    max_steps: int = 16
    max_file_read_tokens: int = 3000
    max_file_screenshots: int = 2
    model: LLMConfig = field(default_factory=lambda: LLMConfig(
        call_target=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"),
        model=os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini"),
        extract_body={"temperature": 0.3, "max_tokens": 8192}
    ))
    model_multimodal: LLMConfig = field(default_factory=lambda: LLMConfig(
        call_target=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"),
        model=os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini"),
        extract_body={"temperature": 0.0, "max_tokens": 8192}
    ))


@dataclass
class CKAgentConfig:
    """Core CKAgent configuration"""
    name: str = "ck_agent"
    description: str = "Cognitive Kernel, an initial autopilot system."
    max_steps: int = 16
    max_time_limit: int = 4200
    recent_steps: int = 5
    obs_max_token: int = 8192
    exec_timeout_with_call: int = 1000
    exec_timeout_wo_call: int = 200
    end_template: str = "more"  # less|medium|more controls ck_end verbosity (default: more)
    model: LLMConfig = field(default_factory=lambda: LLMConfig(
        call_target=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
        api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"),
        model=os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini"),
        extract_body={"temperature": 0.6, "max_tokens": 4000}
    ))


@dataclass
class LoggingConfig:
    """Centralized logging configuration"""
    console_level: str = "INFO"
    log_dir: str = "logs"
    session_logs: bool = True


@dataclass
class SearchConfig:
    """Search backend configuration"""
    backend: str = "google"  # google|duckduckgo




@dataclass
class EnvironmentConfig:
    """System environment configuration"""


@dataclass
class Settings:
    """Root configuration object"""
    ck: CKAgentConfig = field(default_factory=CKAgentConfig)
    web: WebAgentConfig = field(default_factory=WebAgentConfig)
    file: FileAgentConfig = field(default_factory=FileAgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)

    @classmethod
    def load(cls, path: str = "config.toml") -> "Settings":
        """Load configuration from TOML file or build from environment.

        If the TOML file does not exist and OPENAI_* environment variables are
        provided, build settings that source credentials from environment vars.
        Falls back to hardcoded defaults otherwise.
        """
        try:
            import tomllib
        except ImportError:
            # Python < 3.11 fallback
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError(
                    "TOML support requires Python 3.11+ or 'pip install tomli'"
                )

        config_path = Path(path)

        if not config_path.exists():
            # Environment-only path: create minimal sections so env fallback triggers
            env_vars = {
                "OPENAI_API_BASE": os.environ.get("OPENAI_API_BASE"),
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
                "OPENAI_API_MODEL": os.environ.get("OPENAI_API_MODEL")
            }

            env_present = bool(env_vars["OPENAI_API_BASE"] or env_vars["OPENAI_API_KEY"] or env_vars["OPENAI_API_MODEL"])

            if env_present:
                data: Dict[str, Any] = {
                    "ck": {"model": {}},
                    "web": {"model": {}, "model_multimodal": {}},
                    "file": {"model": {}, "model_multimodal": {}},
                }
                return cls._from_dict(data)
            else:
                return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Convert TOML dict to Settings object"""
        # Extract sections with defaults
        ck_data = data.get("ck", {})
        web_data = data.get("web", {})
        file_data = data.get("file", {})
        logging_data = data.get("logging", {})
        search_data = data.get("search", {})
        environment_data = data.get("environment", {})

        # Build nested configs
        ck_config = CKAgentConfig(
            name=ck_data.get("name", "ck_agent"),
            description=ck_data.get("description", "Cognitive Kernel, an initial autopilot system."),
            max_steps=ck_data.get("max_steps", 16),
            max_time_limit=ck_data.get("max_time_limit", 4200),
            recent_steps=ck_data.get("recent_steps", 5),
            obs_max_token=ck_data.get("obs_max_token", 8192),
            exec_timeout_with_call=ck_data.get("exec_timeout_with_call", 1000),
            exec_timeout_wo_call=ck_data.get("exec_timeout_wo_call", 200),
            end_template=ck_data.get("end_template", "more"),
            # Always build model (even if empty dict) so env fallback can apply
            model=cls._build_llm_config(ck_data.get("model", {}), {
                "temperature": 0.6, "max_tokens": 4000
            })
        )

        web_config = WebAgentConfig(
            max_steps=web_data.get("max_steps", 20),
            use_multimodal=web_data.get("use_multimodal", "auto"),
            model=cls._build_llm_config(web_data.get("model", {}), {
                "temperature": 0.0, "max_tokens": 8192
            }),
            model_multimodal=cls._build_llm_config(web_data.get("model_multimodal", {}), {
                "temperature": 0.0, "max_tokens": 8192
            }),
            env=cls._build_web_env_config(web_data.get("env", {})),
            env_builtin=cls._build_web_env_builtin_config(web_data.get("env_builtin", {}))
        )

        file_config = FileAgentConfig(
            max_steps=file_data.get("max_steps", 16),
            max_file_read_tokens=file_data.get("max_file_read_tokens", 3000),
            max_file_screenshots=file_data.get("max_file_screenshots", 2),
            model=cls._build_llm_config(file_data.get("model", {}), {
                "temperature": 0.3, "max_tokens": 8192
            }),
            model_multimodal=cls._build_llm_config(file_data.get("model_multimodal", {}), {
                "temperature": 0.0, "max_tokens": 8192
            })
        )

        logging_config = LoggingConfig(
            console_level=logging_data.get("console_level", "INFO"),
            log_dir=logging_data.get("log_dir", "logs"),
            session_logs=logging_data.get("session_logs", True)
        )

        search_config = SearchConfig(
            backend=search_data.get("backend", "google")
        )

        environment_config = EnvironmentConfig()

        return cls(
            ck=ck_config,
            web=web_config,
            file=file_config,
            logging=logging_config,
            search=search_config,
            environment=environment_config
        )

    @staticmethod
    def _build_llm_config(llm_data: Dict[str, Any], default_extract_body: Dict[str, Any]) -> LLMConfig:
        """Build LLMConfig from TOML data - HTTP-only, fail-fast

        Priority order: TOML config > Inheritance > Environment variables > Hardcoded defaults

        Environment variable support:
        - OPENAI_API_BASE: Default API base URL
        - OPENAI_API_KEY: Default API key
        - OPENAI_API_MODEL: Default model name

        Environment variables are only used when the corresponding config value is not provided.
        """
        # Merge default extract_body with config
        extract_body = default_extract_body.copy()
        extract_body.update(llm_data.get("extract_body", {}))
        # Also support legacy call_kwargs section for backward compatibility
        extract_body.update(llm_data.get("call_kwargs", {}))

        # HTTP-only validation and environment variable fallback
        call_target = llm_data.get("call_target")
        if call_target is None:
            call_target = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions")

        # Validate HTTP URL regardless of source (config or env var)
        if not call_target.startswith("http"):
            raise ValueError(f"call_target must be HTTP URL, got: {call_target}")

        api_key = llm_data.get("api_key")
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "your-api-key-here")

        model = llm_data.get("model")
        if not model:
            model = os.environ.get("OPENAI_API_MODEL", "gpt-4o-mini")

        # Extract api_base_url from call_target only if explicitly requested
        api_base_url = llm_data.get("api_base_url")
        # Do not auto-extract from call_target to preserve inheritance behavior

        config = LLMConfig(
            call_target=call_target,
            api_key=api_key,
            model=model,
            api_base_url=api_base_url,
            request_timeout=llm_data.get("request_timeout", 600),
            max_retry_times=llm_data.get("max_retry_times", 5),
            max_token_num=llm_data.get("max_token_num", 20000),
            extract_body=extract_body,
            thinking=llm_data.get("thinking", False),
            seed=llm_data.get("seed", 1377),
        )

        return config

    @staticmethod
    def _build_web_env_config(env_data: Dict[str, Any]) -> WebEnvConfig:
        """Build WebEnvConfig from TOML data"""
        return WebEnvConfig(
            web_ip=env_data.get("web_ip", "localhost:3000"),
            web_command=env_data.get("web_command", ""),
            web_timeout=env_data.get("web_timeout", 600),
            screenshot_boxed=env_data.get("screenshot_boxed", True),
            target_url=env_data.get("target_url", "https://www.bing.com/")
        )

    @staticmethod
    def _build_web_env_builtin_config(env_data: Dict[str, Any]) -> WebEnvBuiltinConfig:
        """Build WebEnvBuiltinConfig from TOML data"""
        return WebEnvBuiltinConfig(
            max_browsers=env_data.get("max_browsers", 16),
            headless=env_data.get("headless", True),
            web_timeout=env_data.get("web_timeout", 600),
            screenshot_boxed=env_data.get("screenshot_boxed", True),
            target_url=env_data.get("target_url", "https://www.bing.com/")
        )

    def validate(self) -> None:
        """Validate configuration values"""
        # Validate use_multimodal enum
        if self.web.use_multimodal not in {"off", "yes", "auto"}:
            raise ValueError(f"web.use_multimodal must be 'off', 'yes', or 'auto', got: {self.web.use_multimodal}")

        # Validate search backend
        if self.search.backend not in {"google", "duckduckgo"}:
            raise ValueError(f"search.backend must be 'google' or 'duckduckgo', got: {self.search.backend}")

        # Validate std_logging level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.logging.console_level not in valid_levels:
            raise ValueError(f"logging.console_level must be one of {valid_levels}, got: {self.logging.console_level}")

    def to_ckagent_kwargs(self) -> Dict[str, Any]:
        """Convert Settings to CKAgent constructor kwargs"""
        # Parent→child inheritance for API creds
        parent_model = self._llm_config_to_dict(self.ck.model)
        web_model = self._llm_config_to_dict(self.web.model)
        file_model = self._llm_config_to_dict(self.file.model)
        web_mm_model = self._llm_config_to_dict(self.web.model_multimodal)
        file_mm_model = self._llm_config_to_dict(self.file.model_multimodal)

        def inherit(child: Dict[str, Any], parent: Dict[str, Any]) -> Dict[str, Any]:
            # Inherit fields that are missing or empty in child
            if ("api_base_url" not in child or not child.get("api_base_url")) and "api_base_url" in parent:
                child["api_base_url"] = parent["api_base_url"]
            if ("api_key" not in child or not child.get("api_key")) and "api_key" in parent:
                child["api_key"] = parent["api_key"]
            if ("model" not in child or not child.get("model")) and "model" in parent:
                child["model"] = parent["model"]
            return child

        web_model = inherit(web_model, parent_model)
        file_model = inherit(file_model, parent_model)
        web_mm_model = inherit(web_mm_model, parent_model)
        file_mm_model = inherit(file_mm_model, parent_model)

        # Legacy tests expect a reduced model dict with call_kwargs etc.
        def reduce_model(m: Dict[str, Any]) -> Dict[str, Any]:
            out = {
                "call_target": m.get("call_target"),
                "thinking": m.get("thinking", False),
                "request_timeout": m.get("request_timeout", 600),
                "max_retry_times": m.get("max_retry_times", 5),
                "seed": m.get("seed", 1377),
                "max_token_num": m.get("max_token_num", 20000),
                "call_kwargs": m.get("extract_body", {}),
            }
            # Preserve API credentials for integration tests that assert existence
            if m.get("api_key") is not None:
                out["api_key"] = m["api_key"]
            if m.get("api_base_url") is not None:
                out["api_base_url"] = m["api_base_url"]
            if m.get("model") is not None:
                out["model"] = m["model"]
            return out

        return {
            "name": self.ck.name,
            "description": self.ck.description,
            "max_steps": self.ck.max_steps,
            "max_time_limit": self.ck.max_time_limit,
            "recent_steps": self.ck.recent_steps,
            "obs_max_token": self.ck.obs_max_token,
            "exec_timeout_with_call": self.ck.exec_timeout_with_call,
            "exec_timeout_wo_call": self.ck.exec_timeout_wo_call,
            "end_template": self.ck.end_template,
            "model": reduce_model(parent_model),
            "web_agent": {
                "max_steps": self.web.max_steps,
                "use_multimodal": self.web.use_multimodal,
                "model": reduce_model(web_model),
                "model_multimodal": reduce_model(web_mm_model),
                "web_env_kwargs": {
                    "web_ip": self.web.env.web_ip,
                    "web_command": self.web.env.web_command,
                    "web_timeout": self.web.env.web_timeout,
                    "screenshot_boxed": self.web.env.screenshot_boxed,
                    "target_url": self.web.env.target_url,
                    # Builtin env config for fuse fallback
                    "max_browsers": self.web.env_builtin.max_browsers,
                    "headless": self.web.env_builtin.headless,
                }
            },
            "file_agent": {
                "max_steps": self.file.max_steps,
                "max_file_read_tokens": self.file.max_file_read_tokens,
                "max_file_screenshots": self.file.max_file_screenshots,
                "model": reduce_model(file_model),
                "model_multimodal": reduce_model(file_mm_model),
            },
            "search_backend": self.search.backend,  # Add search backend configuration
        }

    def _llm_config_to_dict(self, llm_config: LLMConfig) -> Dict[str, Any]:
        """Convert LLMConfig to dict for agent initialization - HTTP-only"""
        return {
            "call_target": llm_config.call_target,
            "api_key": llm_config.api_key,
            "model": llm_config.model,
            "extract_body": llm_config.extract_body.copy(),
            "request_timeout": llm_config.request_timeout,
            "max_retry_times": llm_config.max_retry_times,
            "max_token_num": llm_config.max_token_num,
            # Backward compatibility (ignored by LLM)
            "thinking": llm_config.thinking,
            "seed": llm_config.seed,
        }

    def build_logger(self) -> std_logging.Logger:
        """Create configured logger instance"""
        # Create logs directory
        log_dir = Path(self.logging.log_dir)
        log_dir.mkdir(exist_ok=True)

        # Create logger
        logger = std_logging.getLogger("CognitiveKernel")
        logger.setLevel(getattr(std_logging, self.logging.console_level))

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = std_logging.StreamHandler()
        console_handler.setLevel(getattr(std_logging, self.logging.console_level))
        console_formatter = std_logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler if session_logs enabled
        if self.logging.session_logs:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"ck_session_{timestamp}.log"
            file_handler = std_logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(getattr(std_logging, self.logging.console_level))
            file_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)

        return logger
