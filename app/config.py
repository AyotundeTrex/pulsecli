"""
Holds the settings for a single load test run — the target URL, how many
virtual users to simulate, how long to run, the timeout per request, etc.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.exceptions import ConfigError


@dataclass
class Config:
    """
    The validated settings for one load test run.

    Using a dataclass here (instead of just passing a dictionary
    around) means every other file in this project can trust that
    a Config object it receives is already valid — url is a real
    string, users is a positive number, etc. That trust is only
    possible because validate() runs before this object is used
    anywhere else.
    """
    url: str
    users: int
    duration: int
    timeout: float = 10.0
    method: str = "GET"

    def validate(self) -> None:
        """
        Check that every value makes real-world sense.

        This runs once, right after the Config is built, so that if
        something is wrong (e.g. --users -5), the program stops
        immediately with a clear message — instead of starting a
        "test" that silently does nothing or crashes deep inside
        the concurrency code where the real cause would be hard to see.
        """
        if not self.url or not self.url.strip():
            raise ConfigError("A target URL is required (--url).")

        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ConfigError(
                f"URL must start with http:// or https:// (got: {self.url!r})"
            )

        if self.users <= 0:
            raise ConfigError(f"--users must be a positive number (got: {self.users})")

        if self.duration <= 0:
            raise ConfigError(f"--duration must be a positive number (got: {self.duration})")

        if self.timeout <= 0:
            raise ConfigError(f"--timeout must be a positive number (got: {self.timeout})")

        if self.method != "GET":
            raise ConfigError(
                f"Version 1 only supports GET requests (got: {self.method!r}). "
                "POST support is planned for a later version."
            )


def load_config_file(path: str) -> dict:
    """
    Read a JSON config file and return it as a plain dictionary.

    Kept separate from Config itself so that "reading a file" and
    "validating settings" are two distinct, independently testable
    steps — Stage 7's tests can call this function with a fake file
    path without needing a full Config object involved at all.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with file_path.open("r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file is not valid JSON: {e}")


def build_config(cli_args: dict, config_file_path: str | None = None) -> Config:
    """
    Combine a config file (if given) with command-line arguments into
    one final Config, then validate it.

    Precedence rule: command-line arguments always win over the config
    file. The file supplies defaults; anything the user actually typed
    on the command line overrides those defaults. This matters because
    silently doing it the other way around would mean a --url you type
    gets ignored in favor of a stale value sitting in a JSON file —
    exactly the kind of silent wrong-target bug a QA tool cannot afford.

    cli_args should only contain keys the user *actually* passed
    (None values for anything not provided) — see cli.py for how
    that's built from argparse.
    """
    merged: dict = {}

    if config_file_path:
        merged.update(load_config_file(config_file_path))

    for key, value in cli_args.items():
        if value is not None:
            merged[key] = value

    if "url" not in merged:
        raise ConfigError(
            "No target URL provided. Pass --url or include \"url\" in a --config file."
        )

    config = Config(
        url=merged["url"],
        users=int(merged.get("users", 10)),
        duration=int(merged.get("duration", 30)),
        timeout=float(merged.get("timeout", 10.0)),
        method=merged.get("method", "GET"),
    )
    config.validate()
    return config

