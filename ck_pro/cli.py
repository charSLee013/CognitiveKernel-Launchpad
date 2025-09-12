#!/usr/bin/env python3
# NOTICE: This file is adapted from Tencent's CognitiveKernel-Pro (https://github.com/Tencent/CognitiveKernel-Pro).
# Modifications in this fork (2025) are for academic research and educational use only; no commercial use.
# Original rights belong to the original authors and Tencent; see upstream license for details.

"""
Clean CLI interface for CognitiveKernel-Pro
Simple, direct interface for reasoning tasks.

Following Linus principles:
- Do one thing well
- Fail fast
- Simple interfaces
- No magic
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Iterator, Dict, Any, Optional

try:
    from .core import CognitiveKernel, ReasoningResult
    from .agents.utils import rprint
    from .config.settings import Settings
except ImportError:
    # Direct execution fallback
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ck_pro.core import CognitiveKernel, ReasoningResult
    from ck_pro.agents.utils import rprint
    from ck_pro.config.settings import Settings


def get_args():
    """Parse command line arguments - simple and direct"""
    parser = argparse.ArgumentParser(
        prog="ck-pro",
        description="CognitiveKernel-Pro: Clean reasoning interface"
    )

    # Core arguments
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.toml",
        help="Configuration file path (default: config.toml)"
    )

    # Input/Output
    parser.add_argument(
        "question",
        nargs="?",
        help="Single question to reason about"
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input file (text/questions) for batch processing"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file for results (JSON format)"
    )

    # Behavior
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - prompt for questions"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with timing and step information"
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        help="Maximum reasoning steps (overrides config)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout in seconds (overrides config)"
    )

    return parser.parse_args()


def read_questions(input_source: Optional[str]) -> Iterator[Dict[str, Any]]:
    """
    Read questions from various sources.

    Args:
        input_source: File path, question string, or None for interactive

    Yields:
        Dict with 'id', 'question'
    """
    if not input_source:
        # Interactive mode
        idx = 0
        while True:
            try:
                question = input("Question: ").strip()
                if not question or question.lower() in ['quit', 'exit', '__END__']:
                    break
                yield {
                    'id': f"interactive_{idx:04d}",
                    'question': question
                }
                idx += 1
            except (KeyboardInterrupt, EOFError):
                break

    elif Path(input_source).exists():
        # File input - read plain text file with one question per line
        idx = 0
        with open(input_source, 'r') as f:
            for line_num, line in enumerate(f, 1):
                question = line.strip()
                if not question:
                    continue

                yield {
                    'id': f"file_{idx:04d}",
                    'question': question
                }
                idx += 1

    else:
        # Treat as single question string
        yield {
            'id': 'single_question',
            'question': input_source
        }


def write_result(result_data: Dict[str, Any], output_file: Optional[str] = None):
    """Write result to output file or stdout"""
    if output_file:
        with open(output_file, 'a') as f:
            f.write(result_data['answer'] + '\n')
    else:
        # Pretty print to stdout
        if 'answer' in result_data:
            print(f"Answer: {result_data['answer']}")
        if 'reasoning_steps' in result_data:
            print(f"Steps: {result_data['reasoning_steps']}")
        if 'execution_time' in result_data:
            print(f"Time: {result_data['execution_time']:.2f}s")


def main():
    """Main CLI entry point"""
    args = get_args()

    try:
        # Create kernel (supports env-only when no TOML file)
        settings = Settings.load(args.config)
        kernel = CognitiveKernel(settings)
        if args.verbose:
            if Path(args.config).exists():
                rprint(f"[blue]Loaded configuration from {args.config}[/blue]")
            else:
                rprint("[blue]No config file found; using environment variables (if set) or built-in defaults[/blue]")

        # Prepare output file
        if args.output:
            # Clear output file
            Path(args.output).write_text('')

        # Process questions
        total_questions = 0
        successful_answers = 0
        total_time = 0.0

        # Build reasoning kwargs
        reasoning_kwargs = {}
        if args.max_steps:
            reasoning_kwargs['max_steps'] = args.max_steps
        if args.timeout:
            reasoning_kwargs['max_time_limit'] = args.timeout
        if args.verbose:
            reasoning_kwargs['include_session'] = True

        # Determine input source: positional argument, --input flag, or interactive
        input_source = args.question or args.input
        if not input_source and not args.interactive:
            rprint("[red]Error: No question provided. Use a positional argument, --input, or --interactive[/red]")
            sys.exit(1)

        for question_data in read_questions(input_source):
            total_questions += 1
            question = question_data['question']

            try:
                # Reason about the question
                result = kernel.reason(question, **reasoning_kwargs)

                # Write result
                reasoning_steps = len(result.session.steps) if result.session else 0
                result_data = {
                    'answer': result.answer,
                    'reasoning_steps': reasoning_steps,
                    'execution_time': result.execution_time
                }
                write_result(result_data, args.output)

                successful_answers += 1
                total_time += result.execution_time

            except Exception as e:
                raise RuntimeError(f"Processing failed: {e}") from e

        # Summary
        if total_questions > 1:
            rprint(f"\n[blue]Summary:[/blue]")
            rprint(f"  Total questions: {total_questions}")
            rprint(f"  Successful: {successful_answers}")
            rprint(f"  Failed: {total_questions - successful_answers}")
            rprint(f"  Total time: {total_time:.2f}s")
            if successful_answers > 0:
                rprint(f"  Average time: {total_time/successful_answers:.2f}s")

    except KeyboardInterrupt:
        rprint("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        rprint(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
