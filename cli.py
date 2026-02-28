#!/usr/bin/env python3
"""Multi-LLM Fan-Out & Evaluation System — CLI entry point."""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.pipeline import run_pipeline
from src.display import (
    print_header,
    print_prompt,
    print_round1,
    print_round2,
    print_round3,
    print_skip_eval_message,
    print_error,
)
from src.utils import setup_logging

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def save_result(result_dict: dict) -> Path:
    """Save result as JSON and return the file path."""
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    short_id = uuid4().hex[:6]
    filename = f"{ts}_{short_id}.json"
    filepath = RESULTS_DIR / filename

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **result_dict,
    }

    filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    return filepath


def read_interactive_prompt() -> str:
    """Read multi-line input; send on double-Enter."""
    print("\nEnter your prompt (press Enter twice to send, Ctrl+C to cancel):\n")
    lines = []
    empty_count = 0
    try:
        while True:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append(line)
            else:
                empty_count = 0
                lines.append(line)
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)

    return "\n".join(lines).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-LLM Fan-Out & Evaluation System",
        epilog="Example: python cli.py \"What is the best programming language?\"",
    )

    parser.add_argument("prompt", nargs="?", help="The prompt to send to all models")
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="Interactive mode (multi-line input, double-Enter to send)",
    )
    parser.add_argument(
        "-f", "--file", type=str, metavar="PATH",
        help="Read prompt from a file",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--models", type=str,
        help="Comma-separated list of models to use (e.g. claude,gpt4o,gemini,grok)",
    )
    parser.add_argument(
        "--no-eval", action="store_true",
        help="Skip the evaluation round (just get raw responses)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose debug logging",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    # Determine the prompt
    prompt = None
    if args.interactive:
        prompt = read_interactive_prompt()
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print_error(f"File not found: {args.file}")
            sys.exit(1)
        prompt = path.read_text().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        print_error(
            "No prompt provided. Use a positional argument, -i for interactive, or -f for file."
        )
        sys.exit(1)

    if not prompt:
        print_error("Prompt is empty.")
        sys.exit(1)

    # Parse model subset
    model_subset = None
    if args.models:
        model_subset = [m.strip() for m in args.models.split(",")]

    # Print prompt
    if not args.json_output:
        print_prompt(prompt)

    # Run the pipeline
    result = await run_pipeline(
        prompt=prompt,
        model_subset=model_subset,
        skip_eval=args.no_eval,
    )

    result_dict = result.to_dict()

    # Save results
    filepath = save_result(result_dict)

    if args.json_output:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    else:
        # Display Round 1
        print_round1([r.to_dict() for r in result.responses])

        # Display Round 2 & 3
        if result.judgments:
            print_round2([j.to_dict() for j in result.judgments])
            print_round3({
                "winner": result.final_winner,
                "points": result.points,
                "votes": result.votes,
            })
        elif args.no_eval:
            print_skip_eval_message()
        else:
            successful = sum(1 for r in result.responses if r.error is None)
            if successful < 2:
                print_skip_eval_message()

        print(f"  Results saved to: {filepath}\n")


if __name__ == "__main__":
    asyncio.run(main())
