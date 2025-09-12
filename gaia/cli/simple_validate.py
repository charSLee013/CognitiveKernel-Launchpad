#!/usr/bin/env python3
# NOTICE: This file is adapted from Tencent's CognitiveKernel-Pro (https://github.com/Tencent/CognitiveKernel-Pro).
# Modifications in this fork (2025) are for academic research and educational use only; no commercial use.
# Original rights belong to the original authors and Tencent; see upstream license for details.

"""
GAIA Simple Validator - Minimal CLI for GAIA evaluation
Pipeline: filter → run via CognitiveKernel → LLM judge → write results
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

# Robust imports with fallback to repository root
try:
    from ck_pro.core import CognitiveKernel
    from ck_pro.config.settings import Settings
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from ck_pro.core import CognitiveKernel
    from ck_pro.config.settings import Settings

from gaia.data_loader import load_tasks, filter_tasks, get_task_stats
from gaia.runner import run_single_task


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='GAIA Simple Validator - Minimal evaluation pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tasks without file attachments
  python -m gaia.cli.simple_validate --data metadata.jsonl --config config.toml

  # Run level 2 tasks only, limit to 50
  python -m gaia.cli.simple_validate --data metadata.jsonl --config config.toml --level 2 --count 50

  # Specify output file
  python -m gaia.cli.simple_validate --data metadata.jsonl --config config.toml --output results.jsonl
        """
    )

    parser.add_argument(
        '--data',
        required=True,
        help='Path to GAIA metadata.jsonl file'
    )
    parser.add_argument(
        '--config',
        required=False,
        help='Path to TOML configuration file (optional; environment variables supported)'
    )
    parser.add_argument(
        '--level',
        default='all',
        choices=['1', '2', '3', 'all'],
        help='Filter by difficulty level (default: all)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=0,
        help='Maximum number of tasks to run (0 = no limit)'
    )
    parser.add_argument(
        '--output',
        help='Output JSONL file path (default: output/results_YYYYMMDD_HHMMSS.jsonl)'
    )

    args = parser.parse_args()

    # Load and filter tasks
    print(f"Loading tasks from {args.data}...")
    try:
        all_tasks = load_tasks(args.data)
        print(f"Loaded {len(all_tasks)} total tasks")

        # Show initial stats
        initial_stats = get_task_stats(all_tasks)
        print(f"Initial stats: {initial_stats}")

        # Filter tasks
        tasks = filter_tasks(all_tasks, level=args.level, limit=args.count)
        print(f"After filtering: {len(tasks)} tasks (level={args.level}, limit={args.count})")

        if not tasks:
            print("No tasks to process after filtering. Exiting.")
            sys.exit(0)

    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

    # Initialize CognitiveKernel (support env-only when no --config provided)
    try:
        if args.config and os.path.exists(args.config):
            print(f"Initializing CognitiveKernel from config: {args.config}")
            settings = Settings.load(args.config)
        else:
            print("Initializing CognitiveKernel (no config file); using environment variables if set, otherwise defaults")
            settings = Settings.load(args.config or "config.toml")
        kernel = CognitiveKernel(settings)
        print("CognitiveKernel initialized successfully")
    except Exception as e:
        print(f"Error initializing CognitiveKernel: {e}")
        sys.exit(1)

    # Determine output path
    output_path = args.output
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('output', exist_ok=True)
        output_path = os.path.join('output', f'results_{timestamp}.jsonl')

    print(f"Results will be written to: {output_path}")

    # Process tasks
    results = []
    failed_count = 0

    print(f"\nProcessing {len(tasks)} tasks...")
    print("=" * 60)

    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] Processing task: {task['task_id']}")

        try:
            result = run_single_task(kernel, task)
            results.append(result)

            # Check for execution failure (fail-fast requirement)
            if not result['success']:
                print(f"FAILED: {result['error']}")
                failed_count += 1
                # Fail fast on first kernel failure
                print(f"\nFail-fast triggered: Task {task['task_id']} failed execution")
                print(f"Error: {result['error']}")
                print("Exiting immediately as per fail-fast policy")
                sys.exit(1)
            else:
                print(f"SUCCESS: Score {result['score']}/5 - {result['judge_reason']}")

        except KeyboardInterrupt:
            print("\nInterrupted by user")
            break
        except Exception as e:
            print(f"UNEXPECTED ERROR: {e}")
            failed_count += 1
            # Still fail fast on unexpected errors
            sys.exit(1)

    # Write results
    print(f"\nWriting {len(results)} results to {output_path}")
    try:
        # Ensure parent directory exists (handles --output with nested paths)
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, 'w+', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(f"Results written successfully")
    except Exception as e:
        print(f"Error writing results: {e}")
        sys.exit(1)

    # Summary statistics
    if results:
        successful = [r for r in results if r['success']]
        scores = [r['score'] for r in successful]

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total tasks processed: {len(results)}")
        print(f"Successful executions: {len(successful)}")
        print(f"Failed executions: {failed_count}")

        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"Average score: {avg_score:.2f}/5")
            print(f"Score distribution:")
            for score in range(6):
                count = scores.count(score)
                if count > 0:
                    print(f"  Score {score}: {count} tasks ({count/len(scores)*100:.1f}%)")

        print(f"\nResults saved to: {output_path}")

    print("Evaluation completed successfully")


if __name__ == '__main__':
    main()
