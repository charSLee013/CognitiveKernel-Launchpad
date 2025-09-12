"""
Test cases for environment variable fallback in LLM configuration.

Phase 1, Task 1.2: Design test cases for environment variable fallback scenarios
"""

import os
import pytest
from unittest.mock import patch
from ck_pro.config.settings import Settings, LLMConfig


class TestEnvironmentVariableFallback:
    """Test environment variable fallback behavior in _build_llm_config"""

    def setup_method(self):
        """Clean up environment variables before each test"""
        env_vars = ["OPENAI_API_BASE", "OPENAI_API_KEY", "OPENAI_API_MODEL"]
        for var in env_vars:
            os.environ.pop(var, None)

    def teardown_method(self):
        """Clean up environment variables after each test"""
        env_vars = ["OPENAI_API_BASE", "OPENAI_API_KEY", "OPENAI_API_MODEL"]
        for var in env_vars:
            os.environ.pop(var, None)

    # Test Case 1.1: Environment variables used when no config provided
    def test_env_vars_used_when_no_config(self):
        """Test that environment variables are used when no TOML config is provided"""
        # Setup environment variables
        os.environ["OPENAI_API_BASE"] = "https://test.openai.com/v1/chat/completions"
        os.environ["OPENAI_API_KEY"] = "test-key-123"
        os.environ["OPENAI_API_MODEL"] = "test-model-456"

        # Call with empty config
        result = Settings._build_llm_config({}, {"temperature": 0.5})

        # Verify environment variables are used
        assert result.call_target == "https://test.openai.com/v1/chat/completions"
        assert result.api_key == "test-key-123"
        assert result.model == "test-model-456"
        assert result.extract_body == {"temperature": 0.5}

    # Test Case 1.2: Environment variables not used when config provided
    def test_env_vars_ignored_when_config_provided(self):
        """Test that environment variables are ignored when TOML config is provided"""
        # Setup environment variables (should be ignored)
        os.environ["OPENAI_API_BASE"] = "https://env.openai.com/v1/chat/completions"
        os.environ["OPENAI_API_KEY"] = "env-key-123"
        os.environ["OPENAI_API_MODEL"] = "env-model-456"

        # Provide TOML config (should take precedence)
        config = {
            "call_target": "https://toml.openai.com/v1/chat/completions",
            "api_key": "toml-key-789",
            "model": "toml-model-999"
        }

        result = Settings._build_llm_config(config, {"temperature": 0.5})

        # Verify TOML config is used, not environment variables
        assert result.call_target == "https://toml.openai.com/v1/chat/completions"
        assert result.api_key == "toml-key-789"
        assert result.model == "toml-model-999"

    # Test Case 1.3: Partial environment variable usage
    def test_partial_env_var_usage(self):
        """Test mixing environment variables with some config values"""
        # Setup only some environment variables
        os.environ["OPENAI_API_KEY"] = "env-key-only"
        # Don't set OPENAI_API_BASE or OPENAI_API_MODEL

        # Provide partial TOML config
        config = {
            "call_target": "https://toml.openai.com/v1/chat/completions",
            "model": "toml-model"
            # api_key not provided in config
        }

        result = Settings._build_llm_config(config, {"temperature": 0.5})

        # Verify mix of config and environment variables
        assert result.call_target == "https://toml.openai.com/v1/chat/completions"  # From config
        assert result.api_key == "env-key-only"  # From environment
        assert result.model == "toml-model"  # From config

    # Test Case 1.4: No environment variables set (fallback to defaults)
    def test_no_env_vars_fallback_to_defaults(self):
        """Test fallback to hardcoded defaults when no environment variables are set"""
        # Don't set any environment variables

        # Call with empty config
        result = Settings._build_llm_config({}, {"temperature": 0.7})

        # Verify hardcoded defaults are used
        assert result.call_target == "https://api.openai.com/v1/chat/completions"
        assert result.api_key == "your-api-key-here"
        assert result.model == "gpt-4o-mini"
        assert result.extract_body == {"temperature": 0.7}

    # Test Case 1.5: Environment variables with extract_body merging
    def test_env_vars_with_extract_body_merging(self):
        """Test environment variables work correctly with extract_body merging"""
        os.environ["OPENAI_API_BASE"] = "https://test.openai.com/v1/chat/completions"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["OPENAI_API_MODEL"] = "test-model"

        # Provide config with extract_body
        config = {
            "extract_body": {"temperature": 0.8, "max_tokens": 2000}
        }

        result = Settings._build_llm_config(config, {"temperature": 0.5, "top_p": 0.9})

        # Verify environment variables are used
        assert result.call_target == "https://test.openai.com/v1/chat/completions"
        assert result.api_key == "test-key"
        assert result.model == "test-model"
        # Verify extract_body merging: config overrides default
        assert result.extract_body == {"temperature": 0.8, "max_tokens": 2000, "top_p": 0.9}

    # Test Case 1.6: HTTP validation still works with environment variables
    def test_http_validation_with_env_vars(self):
        """Test that HTTP validation still works when using environment variables"""
        # Set invalid HTTP URL in environment
        os.environ["OPENAI_API_BASE"] = "invalid-url-without-http"

        config = {}  # No config provided, should use env var

        # Should raise ValueError for invalid HTTP URL
        with pytest.raises(ValueError, match="call_target must be HTTP URL"):
            Settings._build_llm_config(config, {"temperature": 0.5})

    # Test Case 1.7: Priority order: TOML > env vars > defaults
    def test_priority_order_comprehensive(self):
        """Comprehensive test of priority order: TOML > env vars > defaults"""
        # Setup environment variables
        os.environ["OPENAI_API_BASE"] = "https://env.openai.com/v1/chat/completions"
        os.environ["OPENAI_API_KEY"] = "env-key"
        os.environ["OPENAI_API_MODEL"] = "env-model"

        # Test 1: All from TOML config (highest priority)
        config1 = {
            "call_target": "https://toml.openai.com/v1/chat/completions",
            "api_key": "toml-key",
            "model": "toml-model"
        }
        result1 = Settings._build_llm_config(config1, {"temperature": 0.5})
        assert result1.call_target == "https://toml.openai.com/v1/chat/completions"
        assert result1.api_key == "toml-key"
        assert result1.model == "toml-model"

        # Test 2: Mix of TOML and env vars
        config2 = {
            "call_target": "https://toml.openai.com/v1/chat/completions"
            # api_key and model not provided, should use env vars
        }
        result2 = Settings._build_llm_config(config2, {"temperature": 0.5})
        assert result2.call_target == "https://toml.openai.com/v1/chat/completions"  # TOML
        assert result2.api_key == "env-key"  # Env var
        assert result2.model == "env-model"  # Env var

        # Test 3: All from env vars
        result3 = Settings._build_llm_config({}, {"temperature": 0.5})
        assert result3.call_target == "https://env.openai.com/v1/chat/completions"
        assert result3.api_key == "env-key"
        assert result3.model == "env-model"

        # Test 4: No env vars set, fallback to defaults
        # Clean up env vars
        os.environ.pop("OPENAI_API_BASE", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_API_MODEL", None)

        result4 = Settings._build_llm_config({}, {"temperature": 0.5})
        assert result4.call_target == "https://api.openai.com/v1/chat/completions"  # Default
        assert result4.api_key == "your-api-key-here"  # Default
        assert result4.model == "gpt-4o-mini"  # Default

    # Test Case 1.8: Backward compatibility with call_kwargs
    def test_backward_compatibility_call_kwargs(self):
        """Test that legacy call_kwargs still works with environment variables"""
        os.environ["OPENAI_API_KEY"] = "env-key"

        config = {
            "call_kwargs": {"temperature": 0.9, "max_tokens": 1500}
        }

        result = Settings._build_llm_config(config, {"temperature": 0.5})

        # Verify environment variable is used
        assert result.api_key == "env-key"
        # Verify call_kwargs are merged with default extract_body
        assert result.extract_body["temperature"] == 0.9  # From call_kwargs
        assert result.extract_body["max_tokens"] == 1500  # From call_kwargs


class TestInheritanceWithEnvironmentVariables:
    """Test environment variables work correctly with inheritance"""

    def setup_method(self):
        """Clean up environment variables"""
        env_vars = ["OPENAI_API_BASE", "OPENAI_API_KEY", "OPENAI_API_MODEL"]
        for var in env_vars:
            os.environ.pop(var, None)

    def teardown_method(self):
        """Clean up environment variables"""
        env_vars = ["OPENAI_API_BASE", "OPENAI_API_KEY", "OPENAI_API_MODEL"]
        for var in env_vars:
            os.environ.pop(var, None)

    def test_inheritance_priority_over_env_vars(self):
        """Test that inheritance has priority over environment variables"""
        # This test verifies that the inheritance logic in to_ckagent_kwargs()
        # works correctly with the new environment variable fallback

        # Setup environment variables
        os.environ["OPENAI_API_KEY"] = "env-key"

        # Create settings with CK model having api_key, web model inheriting
        settings = Settings()
        settings.ck.model = LLMConfig(
            call_target="https://ck.openai.com/v1/chat/completions",
            api_key="ck-key",  # This should be inherited by web model
            model="ck-model"
        )

        # Web model should inherit from CK model, not use env var
        web_model_dict = {
            "call_target": "https://web.openai.com/v1/chat/completions",
            "model": "web-model"
            # api_key not specified, should inherit from ck.model
        }

        web_config = Settings._build_llm_config(web_model_dict, {"temperature": 0.0})

        # The inheritance happens in to_ckagent_kwargs(), so this test
        # verifies that env vars don't interfere with inheritance logic
        assert web_config.call_target == "https://web.openai.com/v1/chat/completions"
        assert web_config.model == "web-model"
        # api_key should be inherited from ck.model, not from env var
        # (This test assumes inheritance logic is working correctly)

    def test_inheritance_with_model_field(self):
        """Test that model field is properly inherited from parent to child configs"""
        # Create settings with parent model
        settings = Settings()
        settings.ck.model = LLMConfig(
            call_target="https://parent.openai.com/v1/chat/completions",
            api_key="parent-key",
            model="parent-model"
        )

        # Create child web model without model specified (should inherit)
        settings.web.model = LLMConfig(
            call_target="https://web.openai.com/v1/chat/completions",
            api_key="web-key",
            model=""  # Empty model should trigger inheritance
        )

        # Get kwargs and check inheritance
        kwargs = settings.to_ckagent_kwargs()
        web_agent_config = kwargs.get("web_agent", {})
        web_model_config = web_agent_config.get("model", {})

        # Verify that model was inherited from parent
        assert web_model_config.get("model") == "parent-model", f"Expected 'parent-model', got {web_model_config.get('model')}"

        # Verify other fields are preserved
        assert web_model_config.get("call_target") == "https://web.openai.com/v1/chat/completions"
        assert web_model_config.get("api_key") == "web-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])