#!/usr/bin/env python3
# NOTICE: This file is adapted from Tencent's CognitiveKernel-Pro (https://github.com/Tencent/CognitiveKernel-Pro).
# Modifications in this fork (2025) are for academic research and educational use only; no commercial use.
# Original rights belong to the original authors and Tencent; see upstream license for details.

"""
CognitiveKernel-Pro Gradio Interface
Simple, direct implementation following Linus Torvalds principles.
No defensive programming, maximum reuse of existing logic.

NOTE:
The CognitiveKernel system previously used signal-based timeouts which had threading
issues. This has been fixed by replacing signal-based timeouts with thread-safe
threading.Timer mechanisms in the CodeExecutor class.
"""

import gradio as gr
from pathlib import Path
import time
from .config.settings import Settings


from .core import CognitiveKernel

def create_interface(kernel):
    """Create modern Gradio chat interface with sidebar layout - inspired by smolagents design"""

    with gr.Blocks(theme="ocean", fill_height=True) as interface:
        # Session state management
        session_state = gr.State({})

        with gr.Sidebar():
            # Header with branding
            gr.Markdown(
                "# 🧠 CognitiveKernel Pro"
                "\n> Advanced AI reasoning system with three-stage cognitive architecture"
            )

            # Example questions section
            with gr.Group():
                gr.Markdown("**💡 Try These Examples**")

                def set_example(example_text):
                    return example_text

                example1_btn = gr.Button("📊 什么是机器学习？", size="sm")
                example2_btn = gr.Button("🌐 What is artificial intelligence?", size="sm")
                example3_btn = gr.Button("🔍 帮我搜索最新的AI发展趋势", size="sm")
                example4_btn = gr.Button("📝 Explain quantum computing", size="sm")

            # Input section with modern grouping
            with gr.Group():
                gr.Markdown("**💬 Your Request**")
                query_input = gr.Textbox(
                    lines=4,
                    label="Chat Message",
                    container=False,
                    placeholder="Enter your question here and press Shift+Enter or click Submit...",
                    show_label=False
                )

                with gr.Row():
                    submit_btn = gr.Button("🚀 Submit", variant="primary", scale=2)
                    clear_btn = gr.Button("🗑️ Clear", scale=1)

            # System info section
            with gr.Group():
                gr.Markdown("**⚙️ System Status**")
                status_display = gr.Textbox(
                    value="Ready for reasoning tasks",
                    label="Status",
                    interactive=False,
                    container=False,
                    show_label=False
                )

            # Branding footer
            gr.HTML(
                "<br><h4><center>Powered by <a target='_blank' href='https://github.com/charSLee013/CognitiveKernel-Launchpad'><b>🧠 CognitiveKernel-Launchpad</b></a></center></h4>"
            )

        # Main chat interface with enhanced features
        chatbot = gr.Chatbot(
            label="CognitiveKernel Assistant",
            type="messages",
            avatar_images=(
                "https://cdn-icons-png.flaticon.com/512/1077/1077114.png",  # User avatar
                "https://cdn-icons-png.flaticon.com/512/4712/4712027.png"   # AI avatar
            ),
            show_copy_button=True,
            resizeable=True,
            scale=1,
            latex_delimiters=[
                {"left": r"$$", "right": r"$$", "display": True},
                {"left": r"$", "right": r"$", "display": False},
                {"left": r"\[", "right": r"\]", "display": True},
                {"left": r"\(", "right": r"\)", "display": False},
            ],
            height=600
        )
        def user_enter(question, history, session_state):
            """Handle user input - add to history and clear input with status update"""
            if not question or not question.strip():
                return "", history, "Ready for reasoning tasks", gr.Button(interactive=True)

            history = history + [{"role": "user", "content": question.strip()}]
            return "", history, "🤔 Processing your request...", gr.Button(interactive=False)

        def ai_response(history, session_state):
            """Handle AI response with enhanced status updates"""
            if not history:
                yield history, "Ready for reasoning tasks", gr.Button(interactive=True)
                return

            # Get the last user message
            user_messages = [msg for msg in history if msg["role"] == "user"]
            if not user_messages:
                yield history, "Ready for reasoning tasks", gr.Button(interactive=True)
                return

            question = user_messages[-1]["content"]
            if not question or not question.strip():
                yield history, "Ready for reasoning tasks", gr.Button(interactive=True)
                return

            try:
                # Phase 2: Process reasoning steps sequentially with status updates
                streaming_generator = kernel.reason(question.strip(), stream=True)
                step_count = 0

                for step_update in streaming_generator:
                    step_type = step_update.get("type", "unknown")
                    result = step_update.get("result")
                    step_count += 1

                    # Update status based on step type
                    if step_type == "start":
                        status = "🎯 Planning approach..."
                    elif step_type == "intermediate":
                        status = f"⚡ Executing step {step_count}..."
                    elif step_type == "complete":
                        status = "✅ Task completed successfully!"
                    else:
                        status = f"🔄 Processing step {step_count}..."

                    if result and result.success:
                        if step_type == "complete":
                            # Final step: build complete response with cleaner formatting
                            final_content = ""
                            if result.answer and result.answer.strip():
                                final_content = result.answer.strip()

                            # Check for explanation display
                            end_style = kernel.settings.ck.end_template if kernel and kernel.settings and kernel.settings.ck else None
                            if end_style in ("medium", "more") and getattr(result, "explanation", None):
                                # Use separator line format for explanation
                                separator_length = 50
                                separator = "─" * separator_length
                                explanation_header = " Explanation "
                                padding_left = (separator_length - len(explanation_header)) // 2
                                padding_right = separator_length - len(explanation_header) - padding_left

                                formatted_explanation = (
                                    "\n\n" +
                                    ("─" * padding_left) + explanation_header + ("─" * padding_right) +
                                    "\n" + result.explanation.strip()
                                )
                                final_content += formatted_explanation

                            content = final_content
                        else:
                            # Intermediate steps: show reasoning
                            if result.reasoning_steps_content and len(result.reasoning_steps_content.strip()) > 0:
                                content = result.reasoning_steps_content.strip()
                            else:
                                content = "Processing..."

                        # Add assistant message
                        history = history + [{"role": "assistant", "content": content}]
                        yield history, status, gr.Button(interactive=False)

                        # Phase 4: Add separator if not final step (following algorithm design)
                        if step_type != "complete":
                            history = history + [{"role": "user", "content": ""}]
                            yield history, status, gr.Button(interactive=False)
                            time.sleep(0.3)  # Visual rhythm from verified pattern

                # Phase 5: Final cleanup and enable input
                while history and history[-1]["role"] == "user" and history[-1]["content"] == "":
                    history.pop()
                    yield history, "✅ Ready for next question", gr.Button(interactive=True)

                yield history, "✅ Ready for next question", gr.Button(interactive=True)

            except Exception as e:
                # Error handling with complete error information
                error_content = f"""🚨 **Critical Processing Error**

I encountered a critical issue while processing your request.

**Error Details:** {str(e)}

The reasoning pipeline encountered an unexpected error. Please try rephrasing your question or contact support if the issue persists."""

                history = history + [{"role": "assistant", "content": error_content}]
                yield history, "❌ Error occurred - Ready for retry", gr.Button(interactive=True)

        # Enhanced event handlers with status updates
        submit_btn.click(
            fn=user_enter,
            inputs=[query_input, chatbot, session_state],
            outputs=[query_input, chatbot, status_display, submit_btn]
        ).then(
            fn=ai_response,
            inputs=[chatbot, session_state],
            outputs=[chatbot, status_display, submit_btn]
        )

        query_input.submit(
            fn=user_enter,
            inputs=[query_input, chatbot, session_state],
            outputs=[query_input, chatbot, status_display, submit_btn]
        ).then(
            fn=ai_response,
            inputs=[chatbot, session_state],
            outputs=[chatbot, status_display, submit_btn]
        )

        clear_btn.click(
            fn=lambda: ([], "🗑️ Chat cleared - Ready for new conversation", gr.Button(interactive=True)),
            inputs=[],
            outputs=[chatbot, status_display, submit_btn]
        )

        # Example button event handlers
        example1_btn.click(
            fn=lambda: "什么是机器学习？",
            inputs=[],
            outputs=[query_input]
        )

        example2_btn.click(
            fn=lambda: "What is artificial intelligence?",
            inputs=[],
            outputs=[query_input]
        )

        example3_btn.click(
            fn=lambda: "帮我搜索最新的AI发展趋势",
            inputs=[],
            outputs=[query_input]
        )

        example4_btn.click(
            fn=lambda: "Explain quantum computing",
            inputs=[],
            outputs=[query_input]
        )


    return interface


def main():
    """Simple CLI entry point"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="CognitiveKernel-Pro Gradio Interface")
    parser.add_argument("--config", "-c", default="config.toml", help="Config file path (optional; environment variables supported)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind to")

    args = parser.parse_args()

    # Build settings: prefer explicit config if present; otherwise env-first
    if args.config and Path(args.config).exists():
        settings = Settings.load(args.config)
    else:
        settings = Settings.load(args.config or "config.toml")

    kernel = CognitiveKernel(settings)
    interface = create_interface(kernel)

    # Launch directly
    interface.launch(
        server_name=args.host,
        server_port=args.port,
        show_error=True
    )


if __name__ == "__main__":
    main()