"""
Entry point for the command line.

    py -m app.cli --url https://example.com --users 10 --duration 30
    py -m app.cli --config test.json
"""

import argparse
import sys

from app.config import build_config
from app.exceptions import ConfigError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    V2 adds: --method now accepts POST/PUT/DELETE too, --header and
    --param are repeatable (action="append"), --body takes a JSON
    string, and --ramp-up is new.
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
        "--method", type=str, default=None, choices=["GET", "POST", "PUT", "DELETE"],
        help="HTTP method",
    )
    parser.add_argument(
        "--header", dest="headers", action="append", default=None,
        help='Custom header, e.g. --header "Authorization: Bearer abc123" (repeatable)',
    )
    parser.add_argument(
        "--param", dest="params", action="append", default=None,
        help='Query parameter, e.g. --param "page=2" (repeatable)',
    )
    parser.add_argument(
        "--body", type=str, default=None,
        help='JSON request body as a string, e.g. --body \'{"username":"trex"}\'',
    )
    parser.add_argument(
        "--ramp-up", dest="ramp_up", type=int, default=None,
        help="Seconds over which virtual users start gradually (default: 0, all at once)",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to a JSON config file. Command-line flags override values in this file "
             "(unless the file defines a multi-step \"steps\" scenario).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    cli_args = {
        "url": args.url,
        "users": args.users,
        "duration": args.duration,
        "timeout": args.timeout,
        "method": args.method,
        "headers": args.headers,
        "params": args.params,
        "body": args.body,
        "ramp_up": args.ramp_up,
    }

    try:
        config = build_config(cli_args, config_file_path=args.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # --- Stage 1 checkpoint output ---
    # Test EXECUTION is intentionally not wired up yet. runner.py and
    # worker.py still expect V1's old (url, users, duration, timeout)
    # signature and haven't been updated for the new Step-based Config.
    # That happens in Stage 2 (http_client) and Stage 5 (scenario
    # execution in worker.py). Right now this just proves config
    # parsing, merging, and validation all work correctly for every
    # new V2 field.
    print("Configuration loaded and validated successfully:\n")
    print(f"  Virtual Users: {config.users}")
    print(f"  Duration:      {config.duration}s")
    print(f"  Timeout:       {config.timeout}s")
    print(f"  Ramp-up:       {config.ramp_up}s")
    print(f"  Steps ({len(config.steps)}):")
    for i, step in enumerate(config.steps, 1):
        label = f" [{step.name}]" if step.name else ""
        print(f"    {i}.{label} {step.method} {step.url}")
        if step.headers:
            print(f"       headers: {step.headers}")
        if step.params:
            print(f"       params:  {step.params}")
        if step.body:
            print(f"       body:    {step.body}")

    print("\n(Test execution is not yet wired up for V2 — that's Stage 2/5. "
          "This confirms configuration parsing only.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
