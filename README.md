# PulseCLI

A simple, beginner-friendly HTTP load testing tool, built in Python.

PulseCLI simulates many concurrent virtual users hitting a target URL and
reports back on how the target performed — total requests, success/failure
counts, response time statistics, throughput, and error rate.

**Status: Version 1 complete.** GET requests, concurrent virtual users,
core metrics, and a full test suite are working end-to-end.

## Why this exists

This project was built as a hands-on way to learn both Python and QA/
performance testing concepts at the same time — concurrency, HTTP request
handling, response-time measurement, and the reasoning behind metrics like
error rate and throughput, not just the code that produces them.

## Installation

Requires Python 3.11 or later.

```bash
git clone https://github.com/AyotundeTrex/pulsecli.git
cd pulsecli
py -m pip install -r requirements.txt
```

## Usage

Run a load test directly from the command line:

```bash
py -m app.cli --url https://example.com --users 10 --duration 30
```

### Available flags

| Flag | Required | Description |
|---|---|---|
| `--url` | Yes (or via `--config`) | Target URL to test |
| `--users` | No (default: 10) | Number of concurrent virtual users |
| `--duration` | No (default: 30) | Test duration in seconds |
| `--timeout` | No (default: 10.0) | Per-request timeout in seconds |
| `--method` | No (default: GET) | HTTP method — only `GET` is supported in V1 |
| `--config` | No | Path to a JSON config file (see below) |

### Using a config file

```bash
py -m app.cli --config examples/example_config.json
```

Example config file (`examples/example_config.json`):
```json
{
  "url": "https://example.com",
  "method": "GET",
  "users": 10,
  "duration": 30,
  "timeout": 10
}
```

**Command-line flags always override config file values.** The file
supplies defaults; anything you actually type on the command line wins.
This lets you keep a saved config for a target and override just one
value for a quick variant test:
```bash
py -m app.cli --config examples/example_config.json --users 50
```

### Example output

```
LOAD TEST RESULTS

Target: https://example.com
Virtual Users: 10
Duration: 30 seconds

Total Requests: 450
Successful: 445
Failed: 5

Average Response Time: 0.72s
Minimum Response Time: 0.31s
Maximum Response Time: 2.81s

Requests/sec: 15.0
Error Rate: 1.11%
```

## Architecture

```
pulsecli/
├── app/
│   ├── cli.py           # entry point, argument parsing, orchestration
│   ├── config.py        # Config dataclass, validation, CLI/file merging
│   ├── http_client.py    # sends one HTTP request, measures it, handles errors
│   ├── worker.py         # simulates ONE virtual user's request loop
│   ├── runner.py         # runs many virtual users concurrently, collects results
│   ├── metrics.py         # turns raw results into aggregate statistics
│   ├── reporter.py       # formats metrics into the final printed report
│   └── exceptions.py      # ConfigError, RequestExecutionError
├── tests/                 # pytest suite — 26 tests, fully mocked, no network required
├── examples/
│   └── example_config.json
└── requirements.txt
```

Each file has exactly one responsibility. This matters in practice, not
just in theory: the metrics calculation logic can be — and is — fully
unit tested without a network connection, a running server, or even a
working CLI, because it's completely isolated from everything else.

## Concurrency model

PulseCLI uses **Python's `asyncio`**, not threads or multiple processes.

Sending an HTTP request and waiting for a response is I/O-bound — almost
all the time is spent *waiting*, not computing. `asyncio` lets many
virtual users' "wait for a response" moments overlap, which is what
actually simulates concurrent traffic. Each virtual user is one `async`
function; `asyncio.gather()` runs all of them at once, and one shared
`httpx.AsyncClient` connection pool is used across every virtual user in
the test.

## Key concepts, briefly

- **Virtual user** — one simulated visitor, repeatedly sending requests
  until the test duration ends.
- **Concurrency** — many virtual users' requests overlapping in time,
  rather than running one after another.
- **Response time** — how long one request took, from sending it to
  receiving the full response.
- **Throughput (Requests/sec)** — total requests completed divided by
  the *actual measured* test duration, not just the requested one.
- **Error rate** — failed requests as a percentage of all requests.
  A request "fails" on a timeout, a connection error, or an HTTP status
  of 400 or above.

## Testing

```bash
py -m pip install pytest pytest-asyncio
py -m pytest -v
```

26 tests across three files, covering config validation, the CLI/file
merge precedence rule, and HTTP request handling (success, timeout,
connection error, 4xx/5xx status). All HTTP tests are mocked — the suite
requires no network connection and never depends on any real website
being online.

## Limitations (Version 1)

- GET requests only — no POST, custom headers, or request bodies yet
- No ramp-up period — all virtual users start at the same instant
- No result export (CSV/JSON) — terminal output only
- Tested at moderate concurrency (tens to low hundreds of virtual users);
  very high user counts haven't been benchmarked yet

## Roadmap

**Phase 2:** ramp-up period, POST request bodies, custom headers, query
parameters, multiple endpoints, CSV/JSON result export

**Phase 3:** HTML report, real-time terminal dashboard, charts, scenario
files, multiple requests per scenario

**Phase 4:** web dashboard, distributed load generation, Docker support,
CI/CD integration, Prometheus/Grafana metrics

## Safety

PulseCLI is built for **authorized performance testing only** — test
systems you own, or have explicit permission to test. It has no stealth
features, no rate-limit bypassing, no credential-attack functionality,
and is not intended or suitable for denial-of-service testing against
systems without permission.

## License

MIT — see [LICENSE](LICENSE).
