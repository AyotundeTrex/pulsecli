"""
Sends a single HTTP request and reports back what happened.

This is the smallest building block in the whole tool — everything else
(virtual users, concurrency, metrics) is built on top of "send one request,
time it, record whether it succeeded."
"""

import time
from dataclasses import dataclass

import httpx

from app.config import Step


@dataclass
class RequestResult:
    """
    Everything worth knowing about one single request.

    This is the one piece of data that flows through the whole rest of
    the program: worker.py produces these, runner.py collects them,
    metrics.py turns a big list of them into the final numbers.

    step_name: which Step (in a scenario) this result belongs to — e.g.
    "login" or "view profile". Empty string for a simple single-URL
    test where there's only one step and a name isn't meaningful. This
    is what will let a future report break results down per-step
    ("login: 50 requests, 2 failed" vs "view profile: 50 requests, 0
    failed") instead of only ever seeing one combined blob of numbers
    for a 4-step scenario.
    """
    timestamp: float          # when the request started (seconds since epoch)
    response_time: float      # how long the request took, in seconds
    status_code: int | None   # the HTTP status code, or None if it never got one
    success: bool             # True if it should count as a "successful" request
    error: str | None = None  # a short description of what went wrong, if anything
    step_name: str = ""       # which scenario step this result belongs to


async def send_request(client: httpx.AsyncClient, step: Step, timeout: float) -> RequestResult:
    """
    Send one request — GET, POST, PUT, or DELETE — as described by a
    Step, and measure what happened.

    Why this takes a Step instead of a plain url string (V1's design):
    a Step carries everything a real request needs — method, headers,
    query parameters, and a JSON body — not just a destination. Using
    client.request(method=..., ...) (httpx's generic method) instead of
    client.get(...) is what makes one function handle all four HTTP
    methods without four nearly-identical copies of this function.

    headers: sent via the `headers=` argument — extra metadata attached
    to the request, like proving who's asking (Authorization) or what
    kind of data is being sent (Content-Type).

    params: sent via `params=` — httpx automatically turns a dict like
    {"page": "2"} into the URL's query string (?page=2) for you; we
    never need to manually build that string ourselves.

    body: sent via `json=` — httpx automatically converts a Python
    dict into a JSON string AND sets the Content-Type header to
    application/json for us. We only pass `json=` at all when there
    IS a body — GET and DELETE requests typically don't send one, and
    passing `json=None` explicitly is different from not passing it,
    so we only include the argument when step.body is truthy.

    Success is still "got a response with a status code under 400" —
    unchanged from V1, still correct regardless of which method was used.
    """
    start = time.perf_counter()
    timestamp = time.time()

    request_kwargs = {
        "method": step.method,
        "url": step.url,
        "timeout": timeout,
    }
    if step.headers:
        request_kwargs["headers"] = step.headers
    if step.params:
        request_kwargs["params"] = step.params
    if step.body:
        request_kwargs["json"] = step.body

    try:
        response = await client.request(**request_kwargs)
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=response.status_code,
            success=response.status_code < 400,
            error=None if response.status_code < 400 else f"HTTP {response.status_code}",
            step_name=step.name,
        )

    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=None,
            success=False,
            error="Request timed out",
            step_name=step.name,
        )

    except httpx.RequestError as e:
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=None,
            success=False,
            error=f"{type(e).__name__}: {e}",
            step_name=step.name,
        )
