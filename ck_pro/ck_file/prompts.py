"""
File prompt management for CognitiveKernel-Pro.

Clean, type-safe prompt building following Linus Torvalds' engineering principles:
- No magic strings or eval() calls
- Clear interfaces and data structures
- Fail fast with proper validation
- Zero technical debt
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pathlib import Path


class PromptType(Enum):
    """Prompt types for file operations"""
    PLAN = "plan"
    ACTION = "action"
    END = "end"


class ActionType(Enum):
    """Valid file action types"""
    LOAD_FILE = "load_file"
    READ_TEXT = "read_text"
    READ_SCREENSHOT = "read_screenshot"
    SEARCH = "search"
    STOP = "stop"

    @classmethod
    def is_valid(cls, action: str) -> bool:
        """Check if action is valid"""
        return action in [item.value for item in cls]


@dataclass
class FileActionResult:
    """Result of a file action"""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_success(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'FileActionResult':
        """Create success result"""
        return cls(True, message, data or {})

    @classmethod
    def create_failure(cls, message: str) -> 'FileActionResult':
        """Create failure result"""
        return cls(False, message, {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }


@dataclass
class FilePromptConfig:
    """Configuration for file prompt generation"""
    max_file_read_tokens: int = 4000
    max_file_screenshots: int = 5

    def __post_init__(self):
        """Validate configuration"""
        if self.max_file_read_tokens <= 0:
            raise ValueError("max_file_read_tokens must be positive")
        if self.max_file_screenshots < 0:
            raise ValueError("max_file_screenshots cannot be negative")


# Template constants - clean separation of content from logic
PLAN_SYSTEM_TEMPLATE = """You are an expert task planner for file agent tasks.

## Available Information
- Target Task: The specific file task to accomplish
- Recent Steps: Latest actions taken by the file agent
- Previous Progress State: JSON representation of task progress

## Progress State Structure
- completed_list (List[str]): Record of completed critical steps
- todo_list (List[str]): Planned future actions (plan multiple steps ahead)
- experience (List[str]): Self-contained notes from past attempts
- information (List[str]): Important collected information for memory

## Guidelines
1. Update progress state based on latest observations
2. Create evaluable Python dictionary (no eval() calls in production)
3. Maintain clean, relevant progress state
4. Document insights in experience field for unproductive attempts
5. Record important page information in information field
6. Stop with N/A if repeated jailbreak/content filter issues
7. Scan the complete file when possible

Example progress state:
{
    "completed_list": ["Scanned last page"],
    "todo_list": ["Count Geoffrey Hinton mentions on penultimate page"],
    "experience": ["Visual information needed - use read_screenshot"],
    "information": ["Three Geoffrey Hinton mentions found on last page"]
}
"""

ACTION_SYSTEM_TEMPLATE = """You are an intelligent file interaction assistant.

Generate Python code using predefined action functions.

## Available Actions
- load_file(file_name: str) -> str: Load file into memory (PDFs to Markdown)
- read_text(file_name: str, page_id_list: list) -> str: Text-only processing
- read_screenshot(file_name: str, page_id_list: list) -> str: Multimodal processing
- search(file_name: str, key_word_list: list) -> str: Keyword search
- stop(answer: str, summary: str) -> str: Conclude task

## Action Guidelines
1. Issue only valid, single actions per step
2. Avoid repetition
3. Always print action results
4. Stop when task completed or unrecoverable errors
5. Use defined functions only - no alternative libraries
6. Load files before reading (load_file first)
7. Use Python code if load_file fails (e.g., unzip archives)
8. Use search only for very long documents with exact keyword needs
9. Read fair amounts: <MAX_FILE_READ_TOKENS tokens, <MAX_FILE_SCREENSHOT images

## Strategy
1. Step-by-step approach for long documents
2. Reflect on previous steps and try alternatives for recurring errors
3. Review progress state and compare with current information
4. Follow See-Think-Act pattern: provide Thought, then Code
"""

END_SYSTEM_TEMPLATE = """Generate well-formatted output for completed file agent tasks.

## Available Information
- Target Task: The specific task accomplished
- Recent Steps: Latest agent actions
- Progress State: JSON representation of task progress
- Final Step: Last action before execution concludes
- Stop Reason: Reason for stopping ("Normal Ending" if complete)

## Guidelines
1. Deliver well-formatted output per task instructions
2. Generate Python dictionary with 'output' and 'log' fields
3. For incomplete tasks: empty output string with detailed log explanations
4. Record partial information in logs for future reference

## Output Examples
Success: {"output": "Found 5 Geoffrey Hinton mentions", "log": "Task completed..."}
Failure: {"output": "", "log": "Incomplete due to max steps exceeded..."}
"""


class FilePromptBuilder:
    """Type-safe prompt builder for file operations"""

    def __init__(self, config: FilePromptConfig):
        self.config = config
        self._templates = {
            PromptType.PLAN: PLAN_SYSTEM_TEMPLATE,
            PromptType.ACTION: ACTION_SYSTEM_TEMPLATE,
            PromptType.END: END_SYSTEM_TEMPLATE
        }

    def build_plan_prompt(
        self,
        task: str,
        recent_steps: str,
        progress_state: Dict[str, Any],
        file_metadata: List[Dict[str, Any]],
        textual_content: str,
        visual_content: Optional[List[str]] = None,
        image_suffix: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Build planning prompt"""
        user_content = self._build_user_content(
            task=task,
            recent_steps=recent_steps,
            progress_state=progress_state,
            file_metadata=file_metadata,
            textual_content=textual_content,
            prompt_type=PromptType.PLAN
        )

        return self._create_message_pair(
            PromptType.PLAN,
            user_content,
            visual_content,
            image_suffix
        )

    def build_action_prompt(
        self,
        task: str,
        recent_steps: str,
        progress_state: Dict[str, Any],
        file_metadata: List[Dict[str, Any]],
        textual_content: str,
        visual_content: Optional[List[str]] = None,
        image_suffix: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Build action prompt"""
        user_content = self._build_user_content(
            task=task,
            recent_steps=recent_steps,
            progress_state=progress_state,
            file_metadata=file_metadata,
            textual_content=textual_content,
            prompt_type=PromptType.ACTION
        )

        return self._create_message_pair(
            PromptType.ACTION,
            user_content,
            visual_content,
            image_suffix
        )

    def build_end_prompt(
        self,
        task: str,
        recent_steps: str,
        progress_state: Dict[str, Any],
        textual_content: str,
        current_step: str,
        stop_reason: str
    ) -> List[Dict[str, Any]]:
        """Build end prompt"""
        user_content = self._build_end_user_content(
            task=task,
            recent_steps=recent_steps,
            progress_state=progress_state,
            textual_content=textual_content,
            current_step=current_step,
            stop_reason=stop_reason
        )

        return self._create_message_pair(PromptType.END, user_content)

    def _build_user_content(
        self,
        task: str,
        recent_steps: str,
        progress_state: Dict[str, Any],
        file_metadata: List[Dict[str, Any]],
        textual_content: str,
        prompt_type: PromptType
    ) -> str:
        """Build user content for plan/action prompts"""
        sections = [
            f"## Target Task\n{task}\n",
            f"## Recent Steps\n{recent_steps}\n",
            f"## Progress State\n{progress_state}\n",
            f"## File Metadata\n{file_metadata}\n",
            f"## Current Content\n{textual_content}\n",
            f"## Target Task (Repeated)\n{task}\n"
        ]

        if prompt_type == PromptType.PLAN:
            sections.append(self._get_plan_output_format())
        elif prompt_type == PromptType.ACTION:
            sections.append(self._get_action_output_format())

        return "\n".join(sections)

    def _build_end_user_content(
        self,
        task: str,
        recent_steps: str,
        progress_state: Dict[str, Any],
        textual_content: str,
        current_step: str,
        stop_reason: str
    ) -> str:
        """Build user content for end prompt"""
        sections = [
            f"## Target Task\n{task}\n",
            f"## Recent Steps\n{recent_steps}\n",
            f"## Progress State\n{progress_state}\n",
            f"## Current Content\n{textual_content}\n",
            f"## Final Step\n{current_step}\n",
            f"## Stop Reason\n{stop_reason}\n",
            f"## Target Task (Repeated)\n{task}\n",
            self._get_end_output_format()
        ]

        return "\n".join(sections)

    def _create_message_pair(
        self,
        prompt_type: PromptType,
        user_content: str,
        visual_content: Optional[List[str]] = None,
        image_suffix: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Create system/user message pair"""
        system_template = self._replace_template_vars(self._templates[prompt_type])

        messages = [
            {"role": "system", "content": system_template},
            {"role": "user", "content": user_content}
        ]

        # Add visual content if provided
        if visual_content:
            messages[1]["content"] = self._add_visual_content(
                user_content, visual_content, image_suffix
            )

        return messages

    def _replace_template_vars(self, template: str) -> str:
        """Replace template variables with config values"""
        return template.replace(
            "MAX_FILE_READ_TOKENS", str(self.config.max_file_read_tokens)
        ).replace(
            "MAX_FILE_SCREENSHOT", str(self.config.max_file_screenshots)
        )

    def _add_visual_content(
        self,
        text_content: str,
        visual_content: List[str],
        image_suffix: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Add visual content to message"""
        if not image_suffix:
            image_suffix = ["png"] * len(visual_content)
        elif len(image_suffix) < len(visual_content):
            image_suffix.extend(["png"] * (len(visual_content) - len(image_suffix)))

        content_parts = [
            {"type": "text", "text": text_content + "\n\n## Screenshot of current pages"}
        ]

        for suffix, img_data in zip(image_suffix, visual_content):
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{suffix};base64,{img_data}"}
            })

        return content_parts

    def _get_plan_output_format(self) -> str:
        """Get output format for plan prompts"""
        return """## Output
Please generate your response in this format:
Thought: {Explain your planning reasoning in one line. Review previous steps, describe new observations, explain your rationale.}
Code: {Output Python dict of updated progress state. Wrap with "```python ```" marks.}
"""

    def _get_action_output_format(self) -> str:
        """Get output format for action prompts"""
        return """## Output
Please generate your response in this format:
Thought: {Explain your action reasoning in one line. Review previous steps, describe new observations, explain your rationale.}
Code: {Output Python code for next action. Issue ONLY ONE action. Wrap with "```python ```" marks.}
"""

    def _get_end_output_format(self) -> str:
        """Get output format for end prompts"""
        return """## Output
Please generate your response in this format:
Thought: {Explain your reasoning for the final output in one line.}
Code: {Output Python dict with final result. Wrap with "```python ```" marks.}
"""

    def _get_base_template(self, prompt_type: PromptType) -> str:
        """Get base template for testing"""
        return self._templates[prompt_type]


# Backward compatibility interface - clean migration path
def create_prompt_builder(
    max_file_read_tokens: int = 4000,
    max_file_screenshots: int = 5
) -> FilePromptBuilder:
    """Factory function for creating prompt builder"""
    config = FilePromptConfig(
        max_file_read_tokens=max_file_read_tokens,
        max_file_screenshots=max_file_screenshots
    )
    return FilePromptBuilder(config)


# Legacy function wrappers for backward compatibility
def file_plan(**kwargs) -> List[Dict[str, Any]]:
    """Legacy wrapper for plan prompt generation"""
    builder = create_prompt_builder(
        max_file_read_tokens=kwargs.get('max_file_read_tokens', 4000),
        max_file_screenshots=kwargs.get('max_file_screenshots', 5)
    )

    return builder.build_plan_prompt(
        task=kwargs['task'],
        recent_steps=kwargs['recent_steps_str'],
        progress_state=kwargs['state'],
        file_metadata=_format_legacy_metadata(kwargs),
        textual_content=kwargs['textual_content'],
        visual_content=kwargs.get('visual_content'),
        image_suffix=kwargs.get('image_suffix')
    )


def file_action(**kwargs) -> List[Dict[str, Any]]:
    """Legacy wrapper for action prompt generation"""
    builder = create_prompt_builder(
        max_file_read_tokens=kwargs.get('max_file_read_tokens', 4000),
        max_file_screenshots=kwargs.get('max_file_screenshots', 5)
    )

    return builder.build_action_prompt(
        task=kwargs['task'],
        recent_steps=kwargs['recent_steps_str'],
        progress_state=kwargs['state'],
        file_metadata=_format_legacy_metadata(kwargs),
        textual_content=kwargs['textual_content'],
        visual_content=kwargs.get('visual_content'),
        image_suffix=kwargs.get('image_suffix')
    )


def file_end(**kwargs) -> List[Dict[str, Any]]:
    """Legacy wrapper for end prompt generation"""
    builder = create_prompt_builder()

    return builder.build_end_prompt(
        task=kwargs['task'],
        recent_steps=kwargs['recent_steps_str'],
        progress_state=kwargs['state'],
        textual_content=kwargs['textual_content'],
        current_step=kwargs['current_step_str'],
        stop_reason=kwargs['stop_reason']
    )


def _format_legacy_metadata(kwargs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format legacy metadata for new interface"""
    return [
        {
            "loaded_files": kwargs.get('loaded_files', []),
            "file_meta_data": kwargs.get('file_meta_data', {})
        }
    ]


# Legacy PROMPTS dict for backward compatibility
PROMPTS = {
    "file_plan": file_plan,
    "file_action": file_action,
    "file_end": file_end,
}
# Clean implementation complete - all legacy code removed
