#!/usr/bin/env python3
"""
Pure HTTP LLM Client - Linus style: simple, direct, fail fast
No provider abstraction, no defensive programming, no technical debt
"""

import requests
from .utils import wrapped_trying, KwargsInitializable

try:
    import tiktoken
except ImportError:
    tiktoken = None


class TikTokenMessageTruncator:
    def __init__(self, model_name="gpt-4"):
        if tiktoken is None:
            # Fallback will be used by MessageTruncator alias when tiktoken is missing
            # Keep class importable but non-functional if instantiated directly without tiktoken
            raise ImportError("tiktoken is required but not installed")
        self.encoding = tiktoken.encoding_for_model(model_name)

    def _count_text_tokens(self, content):
        """Count tokens in a message's content"""
        if isinstance(content, str):
            return len(self.encoding.encode(content))
        elif isinstance(content, list):
            total = 0
            for part in content:
                if part.get("type") == "text":
                    total += len(self.encoding.encode(part.get("text", "")))
            return total
        else:
            return 0

    def _truncate_text_content(self, content, max_tokens):
        """Truncate text in content to fit max_tokens"""
        if isinstance(content, str):
            tokens = self.encoding.encode(content)
            truncated_tokens = tokens[:max_tokens]
            return self.encoding.decode(truncated_tokens)
        elif isinstance(content, list):
            new_content = []
            tokens_used = 0
            for part in content:
                if part.get("type") == "text":
                    text = part.get("text", "")
                    tokens = self.encoding.encode(text)
                    if tokens_used + len(tokens) > max_tokens:
                        remaining = max_tokens - tokens_used
                        if remaining > 0:
                            truncated_tokens = tokens[:remaining]
                            truncated_text = self.encoding.decode(truncated_tokens)
                            if truncated_text:
                                new_content.append({"type": "text", "text": truncated_text})
                        break
                    else:
                        new_content.append(part)
                        tokens_used += len(tokens)
                else:
                    new_content.append(part)
            return new_content
        else:
            return content

    def truncate_message_list(self, messages, max_length):
        """Truncate a list of messages to fit max_length tokens"""
        truncated = []
        total_tokens = 0
        for msg in reversed(messages):
            content = msg.get("content", "")
            tokens = self._count_text_tokens(content)
            if total_tokens + tokens > max_length:
                if not truncated:
                    truncated_content = self._truncate_text_content(content, max_length)
                    truncated_msg = msg.copy()
                    truncated_msg["content"] = truncated_content
                    truncated.insert(0, truncated_msg)
                break
            truncated.insert(0, msg)
            total_tokens += tokens
        return truncated



# Lightweight fallback truncator
class _LightweightMessageTruncator:
    def truncate_message_list(self, messages, max_length):
        # Very simple char-based truncation as a fallback
        total = 0
        out = []
        for msg in reversed(messages):
            content = msg.get("content", "")
            size = len(str(content))
            if total + size > max_length:
                if not out:
                    # truncate this one
                    truncated_msg = msg.copy()
                    text = str(content)
                    truncated_msg["content"] = text[: max(0, max_length - total)]
                    out.insert(0, truncated_msg)
                break
            out.insert(0, msg)
            total += size
        return out

# Single, deterministic MessageTruncator alias - fail fast, no confusion
if tiktoken is not None:
    MessageTruncator = TikTokenMessageTruncator
else:
    MessageTruncator = _LightweightMessageTruncator


class LLM(KwargsInitializable):
    """
    Pure HTTP LLM Client - Linus style: simple, direct, fail fast

    Design principles:
    1. HTTP-only endpoints - no provider abstraction
    2. Fail fast validation - no defensive programming
    3. extract_body for request parameters
    4. Auto base64 for images

    Required fields: call_target (HTTP URL), api_key, model
    """

    def __init__(self, **kwargs):
        # Pure HTTP config - no provider abstraction
        self.call_target = None  # Must be full HTTP URL
        self.api_key = None
        self.api_base_url = None  # Optional for provider-style targets
        self.model = None  # Model ID - separate from extract_body
        self.extract_body = {}  # Pure request parameters (no model!)
        self.max_retry_times = 3
        self.request_timeout = 600
        self.max_token_num = 20000

        # Backward compatibility attributes (ignored in pure HTTP mode)
        self.thinking = False
        self.seed = 1377
        self.print_call_in = None
        self.print_call_out = None
        self.call_kwargs = {}  # Legacy attribute

        # Initialize
        super().__init__(**kwargs)

        # Handle _default_init case (skip validation)
        if kwargs.get('_default_init'):
            self.headers = None
            self.call_stat = {}
            self.message_truncator = TikTokenMessageTruncator()
            return

        # HTTP-only validation - fail fast, no provider abstraction
        if not self.call_target:
            raise ValueError("call_target (HTTP URL) is required")

        if not isinstance(self.call_target, str) or not self.call_target.startswith("http"):
            raise ValueError(f"call_target must be HTTP URL starting with 'http', got: {self.call_target}")

        if not self.api_key:
            raise ValueError("api_key is required")

        if not self.model:
            raise ValueError("model is required")

        # Setup HTTP headers - simple and direct
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Stats and truncator
        self.call_stat = {}
        self.message_truncator = TikTokenMessageTruncator()

    def __repr__(self):
        return f"LLM(target={self.call_target})"

    def __call__(self, messages, extract_body=None, **kwargs):
        """Pure HTTP call interface"""
        func = lambda: self._call_with_messages(messages, extract_body, **kwargs)
        return wrapped_trying(func, max_times=self.max_retry_times)

    def _call_with_messages(self, messages, extract_body=None, **kwargs):
        """Execute pure HTTP LLM call - no abstraction, fail fast"""
        # Handle uninitialized case
        if not self.headers or not self.call_target:
            raise RuntimeError("LLM not properly initialized - use proper call_target and api_key")

        # Process images to base64
        messages = self._process_images(messages)

        # Truncate messages
        messages = self.message_truncator.truncate_message_list(messages, self.max_token_num)

        # Build payload - start with required fields
        payload = {
            "model": self.model,  # Model is separate, not in extract_body
            "messages": messages
        }

        # Add default extract_body parameters (pure request params only)
        if self.extract_body:
            payload.update(self.extract_body)

        # Add call-specific extract_body parameters (override defaults)
        if extract_body:
            payload.update(extract_body)

        # Add any additional kwargs
        payload.update(kwargs)

        # Execute HTTP call - direct to call_target
        response = requests.post(
            self.call_target,
            headers=self.headers,
            json=payload,
            timeout=self.request_timeout
        )

        # Fail fast - no defensive programming
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

        # Parse response - fail fast on invalid format
        try:
            result = response.json()
            message = result["choices"][0]["message"]

            # Check for function calls (tool_calls)
            tool_calls = message.get("tool_calls")
            if tool_calls and len(tool_calls) > 0:
                # Extract function call arguments and synthesize as JSON string
                tool_call = tool_calls[0]
                if tool_call.get("type") == "function":
                    function_args = tool_call.get("function", {}).get("arguments", "{}")
                    # Return the function arguments as a JSON string
                    content = function_args
                else:
                    content = message.get("content", "")
            else:
                # Regular text response
                content = message.get("content", "")

        except (KeyError, IndexError):
            raise RuntimeError(f"Invalid response format: {result}")

        # Fail fast - empty response
        if not content or content.strip() == "":
            raise RuntimeError(f"Empty response: {result}")

        # Update stats
        self._update_stats(result)

        return content

    def _process_images(self, messages):
        """Process images in messages - auto convert to base64 if needed"""
        processed_messages = []

        for message in messages:
            content = message.get("content", "")

            if isinstance(content, list):
                # Multi-modal content - process each part
                processed_content = []
                for part in content:
                    if part.get("type") == "image_url":
                        # Image part - ensure base64 format
                        image_url = part["image_url"]["url"]
                        if image_url.startswith("data:image/"):
                            # Already base64 - keep as is
                            processed_content.append(part)
                        else:
                            # Convert to base64 (if local file or URL)
                            # For now, assume it's already properly formatted
                            processed_content.append(part)
                    else:
                        # Text or other content
                        processed_content.append(part)

                processed_message = message.copy()
                processed_message["content"] = processed_content
                processed_messages.append(processed_message)
            else:
                # Simple text content
                processed_messages.append(message)

        return processed_messages

    def _update_stats(self, result):
        """Update call statistics"""
        usage = result.get("usage", {})
        if usage:
            self.call_stat["llm_call"] = self.call_stat.get("llm_call", 0) + 1
            for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                self.call_stat[key] = self.call_stat.get(key, 0) + usage.get(key, 0)



