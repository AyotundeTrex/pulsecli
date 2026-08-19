"""
Sends a single HTTP request and reports back what happened.

This is the smallest building block in the whole tool — everything else
(virtual users, concurrency, metrics) is built on top of "send one request,
time it, record whether it succeeded."
"""

import time
from dataclasses import dataclass

import httpx


@dataclass
class RequestResult:
    """
    Everything worth knowing about one single request.

    This is the one piece of data that flows through the whole rest of
    the program: worker.py produces these, runner.py collects them,
    metrics.py turns a big list of them into the final numbers. Keeping
    it as one small, clearly-defined object (instead of a loose tuple
    or dict) means every part of the code knows exactly what shape of
    data it's working with.
    """
    timestamp: float          # when the request started (seconds since epoch)
    response_time: float      # how long the request took, in seconds
    status_code: int | None   # the HTTP status code, or None if it never got one
    success: bool             # True if it should count as a "successful" request
    error: str | None = None  # a short description of what went wrong, if anything


async def send_request(client: httpx.AsyncClient, url: str, timeout: float) -> RequestResult:
    """
    Send one GET request and measure what happened.

    Why this takes an existing `client` instead of creating a new
    connection every time: httpx.AsyncClient reuses TCP connections
    under the hood (this is called "connection pooling"). Creating a
    brand new client for every single request would mean re-doing the
    network handshake every time, which is slow and would make our
    load test measure connection setup time instead of the thing we
    actually care about — how the target server performs under load.

    Success is defined here as "got a response with a status code
    under 400." Status codes 200-399 mean the server handled the
    request; 400+ means either the client did something wrong (4xx)
    or the server failed (5xx) — both count as failures for load
    testing purposes, because either way, a real user hitting that
    would experience a broken request.
    """
    start = time.perf_counter()
    timestamp = time.time()

    try:
        response = await client.get(url, timeout=timeout)
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=response.status_code,
            success=response.status_code < 400,
            error=None if response.status_code < 400 else f"HTTP {response.status_code}",
        )

    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=None,
            success=False,
            error="Request timed out",
        )

    except httpx.RequestError as e:
        # Covers connection errors, DNS failures, refused connections, etc.
        # This is deliberately broad — from a load test's point of view,
        # "couldn't connect" and "connection dropped mid-request" are both
        # just failures we need to count, not crash the whole program over.
        elapsed = time.perf_counter() - start
        return RequestResult(
            timestamp=timestamp,
            response_time=elapsed,
            status_code=None,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )

