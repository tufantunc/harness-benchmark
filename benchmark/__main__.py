# benchmark/__main__.py
"""CLI entry point for harness-benchmark."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .task_loader import load_exercises
from .runner import run_benchmark
from .report import generate_report


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark coding agent harnesses")
    parser.add_argument("--config", default="benchmark.yaml", help="Config file path")
    parser.add_argument("--model-url", dest="model_url", help="Override model endpoint URL")
    parser.add_argument("--model-protocol", dest="model_protocol", help="Override API protocol")
    parser.add_argument("--model-name", dest="model_name", help="Override model name")
    parser.add_argument("--harnesses", help="Comma-separated harness list")
    parser.add_argument("--languages", help="Comma-separated languages")
    parser.add_argument("--repetitions", type=int, help="Repetitions per task")
    parser.add_argument("--timeout-sec", dest="timeout_sec", type=int, help="Per-task timeout")
    parser.add_argument("--skip-existing", dest="skip_existing", action="store_true", default=None)
    parser.add_argument("--retry-failed", dest="retry_failed", action="store_true", default=None)
    parser.add_argument("--report-only", dest="report_only", action="store_true", help="Generate report only")
    return parser.parse_args()


def main():
    args = parse_args()

    cli_overrides = {}
    if args.model_url:
        cli_overrides["model_url"] = args.model_url
    if args.model_protocol:
        cli_overrides["model_protocol"] = args.model_protocol
    if args.model_name:
        cli_overrides["model_name"] = args.model_name
    if args.harnesses:
        cli_overrides["harnesses"] = args.harnesses.split(",")
    if args.languages:
        cli_overrides["languages"] = args.languages.split(",")
    if args.repetitions:
        cli_overrides["repetitions"] = args.repetitions
    if args.timeout_sec:
        cli_overrides["timeout_sec"] = args.timeout_sec
    if args.skip_existing is not None:
        cli_overrides["skip_existing"] = args.skip_existing
    if args.retry_failed is not None:
        cli_overrides["retry_failed"] = args.retry_failed

    config = load_config(Path(args.config), cli_overrides)

    if args.report_only:
        generate_report(config)
        return 0

    polyglot_root = Path("polyglot-benchmark")
    exercises = load_exercises(polyglot_root, config.task.languages)
    print(f"Loaded {len(exercises)} exercises")

    summary = run_benchmark(config, exercises)

    generate_report(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
