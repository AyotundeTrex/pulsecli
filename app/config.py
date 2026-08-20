"""
Holds the settings for a single load test run.

V2 change: instead of one url/method/headers baked directly into
Config, every test run is now a Config holding a LIST of Steps. A
"simple" single-endpoint test (what V1 did) is just a Config with one
Step in that list. A multi-step scenario (GET /products -> POST
/login -> GET /profile -> GET /orders) is a Config with several Steps,
executed in order, in a loop, by each virtual user.

This is a deliberate refactor, not a new parallel code path: worker.py
only ever needs to know "loop through these steps in order" — whether
there's 1 step or 10 doesn't change its logic at all.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.exceptions import ConfigError

VALID_METHODS = {"GET", "POST", "PUT", "DELETE"}


@dataclass
class Step:
    """
    ONE request within a test — either the only request in a simple
    test, or one step in a multi-step scenario.

    headers: a dict like {"Authorization": "Bearer abc123"} — extra
    information sent alongside the request. Explained in full when
    http_client.py is updated in Stage 2.

    params: query parameters, the ?key=value part of a URL — e.g.
    {"page": "2"} becomes ?page=2. Kept separate from the base url so
    the same Step could, in principle, be reused with different
    parameter values later.

    body: a Python dict that becomes a JSON request body for POST/PUT
    requests — e.g. {"username": "trex", "password": "secret"} for a
    login request. None for methods that don't send a body (GET,
    DELETE typically don't).
    """
    method: str
    url: str
    name: str = ""
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: dict | None = None

    def validate(self) -> None:
        if not self.url or not self.url.strip():
            raise ConfigError(f"Step '{self.name or self.url}' is missing a URL.")

        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ConfigError(
                f"Step URL must start with http:// or https:// (got: {self.url!r})"
            )

        method = self.method.upper()
        if method not in VALID_METHODS:
            raise ConfigError(
                f"Unsupported method {self.method!r} for step {self.name or self.url!r}. "
                f"Supported methods: {', '.join(sorted(VALID_METHODS))}"
            )
        self.method = method  # normalize e.g. "get" -> "GET"


@dataclass
class Config:
    """
    The validated settings for one load test run.

    steps: always a list, even for a simple single-URL test (a list
    of exactly one Step). This is what lets worker.py stay simple —
    it always just loops through config.steps, regardless of whether
    that's a "real" scenario or a single repeated request.

    ramp_up: seconds over which virtual users start gradually, instead
    of all starting in the same instant. 0 (the default) means the
    old V1 behavior — everyone starts at once. Explained fully when
    ramp-up is implemented in Stage 4.
    """
    users: int
    duration: int
    steps: list[Step]
    timeout: float = 10.0
    ramp_up: int = 0

    def validate(self) -> None:
        """
        Check every value makes real-world sense, including every
        individual step. This runs once, immediately after the Config
        is built, so a mistake anywhere (a bad URL three steps deep in
        a scenario, an unsupported method, a negative ramp-up) is
        caught before a single network request is sent.
        """
        if self.users <= 0:
            raise ConfigError(f"--users must be a positive number (got: {self.users})")

        if self.duration <= 0:
            raise ConfigError(f"--duration must be a positive number (got: {self.duration})")

        if self.timeout <= 0:
            raise ConfigError(f"--timeout must be a positive number (got: {self.timeout})")

        if self.ramp_up < 0:
            raise ConfigError(f"--ramp-up cannot be negative (got: {self.ramp_up})")

        if self.ramp_up >= self.duration:
            raise ConfigError(
                f"--ramp-up ({self.ramp_up}s) must be less than --duration ({self.duration}s) "
                "— otherwise no virtual users would ever finish ramping up before the test ends."
            )

        if not self.steps:
            raise ConfigError(
                "No request steps defined. Pass --url (and optionally --method/--header/"
                "--param/--body), or define \"steps\" in a --config file."
            )

        for step in self.steps:
            step.validate()


def load_config_file(path: str) -> dict:
    """
    Read a JSON config file and return it as a plain dictionary.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with file_path.open("r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file is not valid JSON: {e}")


def _parse_header_list(header_strings: list[str]) -> dict:
    """
    Turns CLI --header values like "Authorization: Bearer abc123" into
    a dict: {"Authorization": "Bearer abc123"}. Each --header flag can
    be repeated to add multiple headers.
    """
    headers = {}
    for entry in header_strings:
        if ":" not in entry:
            raise ConfigError(
                f"Invalid --header format: {entry!r}. Expected \"Key: Value\", e.g. "
                f"\"Authorization: Bearer abc123\""
            )
        key, _, value = entry.partition(":")
        headers[key.strip()] = value.strip()
    return headers


def _parse_param_list(param_strings: list[str]) -> dict:
    """
    Turns CLI --param values like "page=2" into a dict: {"page": "2"}.
    Each --param flag can be repeated to add multiple query parameters.
    """
    params = {}
    for entry in param_strings:
        if "=" not in entry:
            raise ConfigError(
                f"Invalid --param format: {entry!r}. Expected \"key=value\", e.g. \"page=2\""
            )
        key, _, value = entry.partition("=")
        params[key.strip()] = value.strip()
    return params


def build_config(cli_args: dict, config_file_path: str | None = None) -> Config:
    """
    Combine a config file (if given) with command-line arguments into
    one final Config, then validate it.

    Precedence rule, extended for V2: if the config file defines a
    "steps" list (a scenario), that scenario is used as-is — CLI flags
    like --url/--method/--header/--param/--body don't map cleanly onto
    "which of 4 steps do you mean," so they're not applied on top of a
    scenario. --users/--duration/--timeout/--ramp-up still apply as
    overrides either way, since those describe the TEST, not a
    specific request.

    If there's no "steps" key in the file, this behaves like V1: a
    single Step is built by merging the file's url/method/headers/
    params/body with any CLI flags, CLI winning on every field it
    actually provided.
    """
    file_data: dict = {}
    if config_file_path:
        file_data = load_config_file(config_file_path)

    users = cli_args.get("users") if cli_args.get("users") is not None else file_data.get("users", 10)
    duration = cli_args.get("duration") if cli_args.get("duration") is not None else file_data.get("duration", 30)
    timeout = cli_args.get("timeout") if cli_args.get("timeout") is not None else file_data.get("timeout", 10.0)
    ramp_up = cli_args.get("ramp_up") if cli_args.get("ramp_up") is not None else file_data.get("ramp_up", 0)

    if "steps" in file_data:
        steps = [
            Step(
                method=s.get("method", "GET"),
                url=s["url"],
                name=s.get("name", ""),
                headers=s.get("headers", {}),
                params=s.get("params", {}),
                body=s.get("body"),
            )
            for s in file_data["steps"]
        ]
    else:
        url = cli_args.get("url") or file_data.get("url")
        if not url:
            raise ConfigError(
                "No target URL provided. Pass --url, or include \"url\" or \"steps\" "
                "in a --config file."
            )

        method = cli_args.get("method") or file_data.get("method", "GET")

        headers = dict(file_data.get("headers", {}))
        if cli_args.get("headers"):
            headers.update(_parse_header_list(cli_args["headers"]))

        params = dict(file_data.get("params", {}))
        if cli_args.get("params"):
            params.update(_parse_param_list(cli_args["params"]))

        body = file_data.get("body")
        if cli_args.get("body"):
            try:
                body = json.loads(cli_args["body"])
            except json.JSONDecodeError as e:
                raise ConfigError(f"--body is not valid JSON: {e}")

        steps = [Step(method=method, url=url, headers=headers, params=params, body=body)]

    config = Config(
        users=int(users),
        duration=int(duration),
        timeout=float(timeout),
        ramp_up=int(ramp_up),
        steps=steps,
    )
    config.validate()
    return config
