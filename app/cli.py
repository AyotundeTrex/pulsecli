"""
Entry point for the command line.

This is where the program starts when you run:
    py -m app.cli --url https://example.com --users 10 --duration 30
"""

import argparse
import asyncio
import sys
import time

from app.config import build_config
from app.exceptions import ConfigError
from app.metrics import calculate_metrics
from app.reporter import format_report
from app.runner import run_load_test


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Define and parse the command-line arguments.

    Every argument defaults to None (not a real value like 10 or 30).
    That's deliberate: None means "the user didn't type this flag,"
    which is exactly how build_config() in config.py knows whether to
    fall back to a config file value, a built-in default, or raise an
    error. If these defaulted to real numbers instead, we could never
    tell the difference between "the user explicitly chose 10 users"
    and "the user didn't specify, so we picked 10 for them."
    """
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="PulseCLI — a simple, beginner-friendly HTTP load testing tool.",
    )
    parser.add_argument("--url", type=str, default=None, help="Target URL to test")
    parser.add_argument("--users", type=int, default=None, help="Number of virtual users")
    parser.add_argument("--duration", type=int, default=None, help="Test duration in seconds")
    parser.add_argument("--timeout", type=float, default=None, help="Per-request timeout in seconds")
    parser.add_argument(
        "--method", type=str, default=None, choices=["GET"],
        help="HTTP method (only GET is supported in Version 1)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to a JSON config file. Command-line flags override values in this file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    The actual program entry point.

    Returns an exit code (0 = success, 1 = failure) instead of calling
    sys.exit() directly, so this function stays testable — Stage 7's
    tests can call main() and check the return value without the test
    process itself getting killed by sys.exit().
    """
    args = parse_args(argv)

    cli_args = {
        "url": args.url,
        "users": args.users,
        "duration": args.duration,
        "timeout": args.timeout,
        "method": args.method,
    }

    try:
        config = build_config(cli_args, config_file_path=args.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Temporary confirmation output for Stage 2.
    # In Stage 6 this gets replaced by the real "LOAD TEST RESULTS" report —
    # for now, printing the resolved config is how we prove parsing + validation work.
    print(f"Running {config.users} virtual users against {config.url} for {config.duration}s...")
    start = time.perf_counter()
    results = asyncio.run(
        run_load_test(config.url, config.users, config.duration, config.timeout)
    )
    elapsed = time.perf_counter() - start

    metrics = calculate_metrics(results, elapsed)

    print()
    print(format_report(config, metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())

