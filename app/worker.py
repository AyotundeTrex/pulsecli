"""
Simulates ONE virtual user.

A "virtual user" is one simulated visitor: it repeatedly sends requests
to the target until the test duration runs out, and records the result
of every single request it makes.
"""

import time

from app.http_client import RequestResult, send_request


async def run_virtual_user(client, url: str, timeout: float, end_time: float) -> list[RequestResult]:
    """
    Keep sending requests until `end_time` is reached, then stop and
    return everything this one virtual user collected.

    Why `end_time` is a single shared cutoff instead of each worker
    counting its own `duration` seconds: if every virtual user
    independently timed "30 seconds from whenever I personally
    started," small scheduling differences between when each one
    actually got going would drift apart over the run. Calculating
    one end_time up front (in runner.py, before any workers start) and
    handing the same value to every one of them means they all stop at
    exactly the same moment, which is what "10 virtual users for 30
    seconds" is actually supposed to mean.

    Why this returns its own local list instead of writing into one
    shared list: asyncio runs on a single thread, so there's no
    traditional race condition here — but keeping each worker's output
    separate keeps the data flow simple to reason about. One worker
    produces one list; runner.py's job is just to combine the lists,
    not to manage shared, mutable state that many workers write into
    at once.
    """
    results: list[RequestResult] = []
    while time.perf_counter() < end_time:
        result = await send_request(client, url, timeout)
        results.append(result)
    return results

