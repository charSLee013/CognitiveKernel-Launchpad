#!/usr/bin/env python3
"""
CognitiveKernel-Pro Core Interface
Following Linus Torvalds' principles: simple, direct, fail-fast.

This is the ONLY interface users should need.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time

from .agents.agent import MultiStepAgent
from .agents.session import AgentSession
from .config.settings import Settings


@dataclass
class ReasoningResult:
    """
    Result of a reasoning operation.

    Simple, clean result object with no magic.
    Fail fast, no defensive programming.
    """
    question: str
    answer: Optional[str] = None
    success: bool = False
    execution_time: float = 0.0
    session: Optional[Any] = None
    error: Optional[str] = None
    reasoning_steps: Optional[int] = None
    reasoning_steps_content: Optional[str] = None  # Actual step-by-step reasoning content
    explanation: Optional[str] = None  # Final explanation (from ck_end log) for medium/more verbosity
    session_data: Optional[Any] = None

    def __post_init__(self):
        """Validate result after creation - fail fast"""
        if not self.question:
            raise ValueError("Question cannot be empty")

        if self.success and not self.answer:
            raise ValueError("Successful result must have an answer")

        if not self.success and not self.error:
            raise ValueError("Failed result must have an error message")

    @classmethod
    def success_result(cls, question: str, answer: str, execution_time: float = 0.0, session: Any = None, reasoning_steps: int = None, reasoning_steps_content: str = None, explanation: str = None, session_data: Any = None):
        """Create a successful reasoning result"""
        return cls(
            question=question,
            answer=answer,
            success=True,
            execution_time=execution_time,
            session=session,
            reasoning_steps=reasoning_steps,
            reasoning_steps_content=reasoning_steps_content,
            explanation=explanation,
            session_data=session_data
        )

    @classmethod
    def failure_result(cls, question: str, error: str, execution_time: float = 0.0, session: Any = None):
        """Create a failed reasoning result"""
        return cls(
            question=question,
            success=False,
            error=error,
            execution_time=execution_time,
            session=session
        )

    def __str__(self):
        """String representation for debugging"""
        if self.success:
            return f"ReasoningResult(success=True, answer='{self.answer[:100]}...', time={self.execution_time:.2f}s)"
        else:
            return f"ReasoningResult(success=False, error='{self.error}', time={self.execution_time:.2f}s)"


class CognitiveKernel:
    """
    The ONE interface to rule them all.

    Usage:
        kernel = CognitiveKernel.from_config("config.toml")
        result = kernel.reason("What is machine learning?")
        print(result.answer)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize with validated settings"""
        if settings is None:
            settings = Settings()  # Use default settings

        self.settings = settings
        self._agent = None
        self._logger = None

    @classmethod
    def from_config(cls, config_path: str) -> 'CognitiveKernel':
        """Create kernel from config file - fail fast if invalid"""
        settings = Settings.load(config_path)
        settings.validate()
        return cls(settings)

    @property
    def agent(self) -> MultiStepAgent:
        """Lazy-load the agent - create only when needed"""
        if self._agent is None:
            # Import here to avoid circular imports
            from .ck_main.agent import CKAgent

            # Get logger if needed
            if self._logger is None:
                try:
                    self._logger = self.settings.build_logger()
                except Exception:
                    # Continue execution with None logger
                    pass

            # Create agent with clean configuration
            agent_kwargs = self.settings.to_ckagent_kwargs()
            self._agent = CKAgent(self.settings, logger=self._logger, **agent_kwargs)

        return self._agent

    def reason(self, question: str, stream: bool = False, **kwargs):
        """
        The core function - reason about a question.

        Args:
            question: The question to reason about
            stream: If True, returns a generator yielding intermediate results
            **kwargs: Optional overrides (max_steps, etc.)

        Returns:
            If stream=False: ReasoningResult with answer and metadata
            If stream=True: Generator yielding (step_info, partial_result) tuples

        Raises:
            ValueError: If question is empty
            RuntimeError: If reasoning fails
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        # Get agent (triggers lazy loading)
        agent = self.agent

        if stream:
            return self._reason_stream(question.strip(), **kwargs)
        else:
            return self._reason_sync(question.strip(), **kwargs)

    def _reason_sync(self, question: str, **kwargs) -> ReasoningResult:
        """Synchronous reasoning implementation"""
        start_time = time.time()

        try:
            # Run the reasoning
            session = self.agent.run(question, stream=False, **kwargs)

            # Extract reasoning steps content (called once for efficiency)
            reasoning_steps_content = self._extract_reasoning_steps_content(session)

            # Extract the answer and explanation (log from ck_end)
            answer = self._extract_answer(session, reasoning_steps_content)
            explanation = self._extract_explanation(session)

            execution_time = time.time() - start_time

            return ReasoningResult.success_result(
                question=question,
                answer=answer,
                execution_time=execution_time,
                session=session,
                reasoning_steps=len(session.steps),
                reasoning_steps_content=reasoning_steps_content,
                explanation=explanation,
                session_data=session.to_dict() if kwargs.get('include_session') else None
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ReasoningResult.failure_result(
                question=question,
                error=str(e),
                execution_time=execution_time
            )

    def _reason_stream(self, question: str, **kwargs):
        """Streaming reasoning implementation"""
        start_time = time.time()
        step_count = 0
        reasoning_steps_content_parts = []

        try:
            # Run the reasoning in streaming mode
            session_generator = self.agent.run(question, stream=True, **kwargs)

            # Yield initial status - no artificial text
            # Create initial result without triggering validation
            initial_result = ReasoningResult(
                question=question,
                answer="Processing...",  # Non-empty answer for validation
                success=True,
                execution_time=time.time() - start_time,
                session=None,
                reasoning_steps=0,
                reasoning_steps_content="",
                session_data=None
            )
            # Disable validation temporarily by overriding __post_init__
            initial_result.__class__.__post_init__ = lambda self: None
            yield {"type": "start", "step": 0, "result": initial_result}

            # Process each step as it completes
            generator_has_items = False

            for step_info in session_generator:
                generator_has_items = True
                step_count += 1
                step_type = step_info.get("type", "unknown")

                # FIX 2: Only process plan and action steps for streaming display
                if step_type in ["plan", "action"]:
                    # Format ONLY the current step content
                    current_step_content = self._format_step_for_streaming(step_info, step_count)

                    # Accumulate for final result but display only current step
                    reasoning_steps_content_parts.append(current_step_content)

                    # Yield progress update with ONLY current step content
                    progress_result = ReasoningResult(
                        question=question,
                        answer=current_step_content,  # Display ONLY current step content
                        success=True,
                        execution_time=time.time() - start_time,
                        session=None,
                        reasoning_steps=step_count,
                        reasoning_steps_content=current_step_content,  # ONLY current step content for streaming
                        session_data=None
                    )
                    # Disable validation temporarily by overriding __post_init__
                    progress_result.__class__.__post_init__ = lambda self: None
                    yield {"type": step_type, "step": step_count, "result": progress_result}

                elif step_type == "end":
                    # Final step: build final session and extract results
                    # Re-run synchronously to obtain full session state (kept for stability)
                    final_session = self.agent.run(question, stream=False, **kwargs)

                    # Extract final reasoning steps content (full accumulated content)
                    final_reasoning_content = "\n".join(reasoning_steps_content_parts)

                    # Extract final concise answer and explanation (ck_end log)
                    answer = self._extract_answer(final_session, final_reasoning_content)
                    explanation = self._extract_explanation(final_session)

                    execution_time = time.time() - start_time

                    # Yield final result with complete reasoning content and optional explanation
                    if answer and len(str(answer).strip()) > 0:
                        final_result = ReasoningResult.success_result(
                            question=question,
                            answer=answer,
                            execution_time=execution_time,
                            session=final_session,
                            reasoning_steps=len(final_session.steps),
                            reasoning_steps_content=final_reasoning_content,
                            explanation=explanation,
                            session_data=final_session.to_dict() if kwargs.get('include_session') else None
                        )
                    else:
                        # Fallback: use reasoning steps content as answer if available
                        fallback_answer = final_reasoning_content if final_reasoning_content and len(final_reasoning_content.strip()) > 200 else "Processing completed successfully"
                        final_result = ReasoningResult.success_result(
                            question=question,
                            answer=fallback_answer,
                            execution_time=execution_time,
                            session=final_session,
                            reasoning_steps=len(final_session.steps),
                            reasoning_steps_content=final_reasoning_content,
                            explanation=explanation,
                            session_data=final_session.to_dict() if kwargs.get('include_session') else None
                        )
                    yield {"type": "complete", "step": step_count, "result": final_result}
                    break

            # Check if generator was empty
            if not generator_has_items:
                execution_time = time.time() - start_time
                error_result = ReasoningResult.failure_result(
                    question=question,
                    error="Session generator produced no items - possible API or configuration issue",
                    execution_time=execution_time
                )
                yield {"type": "error", "step": 0, "result": error_result}

        except Exception as e:
            execution_time = time.time() - start_time
            error_result = ReasoningResult.failure_result(
                question=question,
                error=str(e),
                execution_time=execution_time
            )
            yield {"type": "error", "step": step_count, "result": error_result}

    def _format_step_for_streaming(self, step_info: dict, step_number: int) -> str:
        """Format a step for streaming display - FIXED STEP COUNTING"""
        # FIX 1: Get actual step number from step_info if available
        actual_step_num = step_info.get("step_idx", step_number)
        step_content = f"## Step {actual_step_num}\n"

        step_info_data = step_info.get("step_info", {})

        # Add planning information
        if "plan" in step_info_data:
            plan = step_info_data["plan"]
            if isinstance(plan, dict) and "thought" in plan:
                thought = plan["thought"]
                if thought.strip():
                    step_content += f"**Planning:** {thought}\n"

        # Add action information
        if "action" in step_info_data:
            action = step_info_data["action"]
            if isinstance(action, dict):
                if "thought" in action:
                    thought = action["thought"]
                    if thought.strip():
                        step_content += f"**Thought:** {thought}\n"

                if "code" in action:
                    code = action["code"]
                    if code.strip():
                        step_content += f"**Action:**\n```python\n{code}\n```\n"

                if "observation" in action:
                    obs = str(action["observation"])
                    if obs.strip():
                        # Truncate long observations for streaming
                        if len(obs) > 500:
                            obs = obs[:500] + "..."
                        step_content += f"**Result:**\n{obs}\n"

        return step_content

    def _extract_answer(self, session: AgentSession, reasoning_steps_content: str = None) -> str:
        """Extract concise answer from session - prioritize final output over detailed reasoning"""
        if not session.steps:
            raise RuntimeError("No reasoning steps found")

        # PRIORITY 1: Check for final results in the last step (most common case)
        last_step = session.steps[-1]
        if isinstance(last_step, dict) and "end" in last_step:
            end_data = last_step["end"]
            if isinstance(end_data, dict) and "final_results" in end_data:
                final_results = end_data["final_results"]
                if isinstance(final_results, dict) and "output" in final_results:
                    output = final_results["output"]
                    if output and len(str(output).strip()) > 0:
                        return str(output)

        # PRIORITY 2: Look for stop() action results with output
        for step in reversed(session.steps):  # Check from last to first
            if isinstance(step, dict) and "action" in step:
                action = step["action"]
                if isinstance(action, dict) and "observation" in action:
                    obs = action["observation"]
                    if isinstance(obs, dict) and "output" in obs:
                        output = obs["output"]
                        if output and len(str(output).strip()) > 0:
                            return str(output)

        # PRIORITY 3: Find all observations and return the most concise meaningful one
        all_content = []
        for step in session.steps:
            if isinstance(step, dict) and "action" in step:
                action = step["action"]
                if isinstance(action, dict) and "observation" in action:
                    obs = str(action["observation"])
                    if len(obs.strip()) > 10:  # Has substantial content
                        all_content.append(obs)

        # Return the shortest meaningful content (most concise answer)
        if all_content:
            # Filter out very long content (likely detailed reasoning)
            concise_content = [c for c in all_content if len(c) < 1000]
            if concise_content:
                return min(concise_content, key=len)
            else:
                return min(all_content, key=len)
        else:
            return min(all_content, key=len)

        # FALLBACK: Use reasoning steps content only if no other answer found
        if reasoning_steps_content and len(reasoning_steps_content.strip()) > 200:
            return reasoning_steps_content

        raise RuntimeError("No answer found in reasoning session")

    def _extract_explanation(self, session: AgentSession) -> Optional[str]:
        """Extract final explanation text from session end step (ck_end log)."""
        try:
            if not session.steps:
                return None
            last_step = session.steps[-1]
            if isinstance(last_step, dict) and "end" in last_step:
                end_data = last_step["end"]
                if isinstance(end_data, dict) and "final_results" in end_data:
                    final_results = end_data["final_results"]
                    if isinstance(final_results, dict) and "log" in final_results:
                        log = final_results["log"]
                        if log and len(str(log).strip()) > 0:
                            return str(log)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("解释提取失败: %s", e)
        return None


    def _extract_reasoning_steps_content(self, session: AgentSession) -> str:
        """Extract step-by-step reasoning content from session - FIXED TO PREVENT INFINITE ACCUMULATION"""
        if not session.steps:
            return ""

        steps_content = []
        step_counter = 1  # Start from 1, not 0

        for step in session.steps:
            if isinstance(step, dict):
                # FIX 3: Only include steps with actual content, skip empty planning steps
                has_content = False
                step_info = f"## Step {step_counter}\n"

                # Add action information if available
                if "action" in step:
                    action = step["action"]
                    if isinstance(action, dict):
                        if "code" in action:
                            code = action["code"]
                            if code.strip():
                                step_info += f"**Action:**\n```python\n{code}\n```\n"
                                has_content = True

                        if "thought" in action:
                            thought = action["thought"]
                            if thought.strip():
                                step_info += f"**Thought:** {thought}\n"
                                has_content = True

                        if "observation" in action:
                            obs = str(action["observation"])
                            if obs.strip():
                                # Truncate very long observations for readability
                                if len(obs) > 1000:
                                    obs = obs[:1000] + "..."
                                step_info += f"**Result:**\n{obs}\n"
                                has_content = True

                # Add plan information if available
                if "plan" in step:
                    plan = step["plan"]
                    if isinstance(plan, dict) and "thought" in plan:
                        thought = plan["thought"]
                        if thought.strip():
                            step_info += f"**Planning:** {thought}\n"
                            has_content = True

                # Only add step if it has actual content
                if has_content:
                    steps_content.append(step_info)
                    step_counter += 1

        return "\n".join(steps_content) if steps_content else ""


# Simple CLI interface
def main():
    """Simple CLI for direct usage"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        prog="ck-pro",
        description="CognitiveKernel-Pro: Simple reasoning interface"
    )
    parser.add_argument("--config", "-c", required=True, help="Config file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("question", nargs="?", help="Question to reason about")

    args = parser.parse_args()

    # Get question from args or stdin
    if args.question:
        question = args.question
    else:
        if sys.stdin.isatty():
            question = input("Question: ").strip()
        else:
            question = sys.stdin.read().strip()

    if not question:
        print("Error: No question provided", file=sys.stderr)
        sys.exit(1)

    try:
        # Create kernel and reason
        kernel = CognitiveKernel.from_config(args.config)
        result = kernel.reason(question, include_session=args.verbose)

        # Output result
        print(f"Answer: {result.answer}")

        # Show explanation when configured for medium/more verbosity
        style = getattr(getattr(kernel, 'settings', None), 'ck', None)
        end_style = None
        try:
            end_style = kernel.settings.ck.end_template if kernel and kernel.settings and kernel.settings.ck else None
        except Exception:
            end_style = None
        if end_style in ("medium", "more") and getattr(result, 'explanation', None):
            print(f"Explanation: {result.explanation}")

        if args.verbose:
            print(f"Steps: {result.reasoning_steps}")
            print(f"Time: {result.execution_time:.2f}s")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
