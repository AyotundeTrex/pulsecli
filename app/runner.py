"""
Coordinates the whole test run.

This is the "conductor" — it doesn't send requests itself, it starts the
right number of virtual users at the same time (concurrently), lets them
run for the configured duration, and then collects their results.
"""

import asyncio
import time

import httpx

from app.http_client import RequestResult
from app.worker import run_virtual_user


async def run_load_test(url: str, users: int, duration: int, timeout: float) -> list[RequestResult]:
    """
    Start `users` virtual users at the same time, let them run
    concurrently for `duration` seconds, and return every result they
    collectively produced.

    Why asyncio.gather(): this is what actually runs multiple async
    functions concurrently. It doesn't run them on separate CPU
    cores — it starts all of them, and each one takes its turn
    whenever it's paused waiting on the network (see the explanation
    in http_client.py and worker.py). Because sending an HTTP request
    and waiting for a reply is almost entirely "waiting," not
    "computing," this is enough to genuinely simulate many users
    hitting the target at once — this is the I/O-bound vs CPU-bound
    distinction from when we chose asyncio in the first place.

    Why one shared httpx.AsyncClient for every virtual user: the
    connection-pooling benefit explained in http_client.py applies
    across the *entire* test this way, not just within one user's
    requests — 10 virtual users sharing one client behaves more like
    10 real browser tabs than 10 completely separate machines.

    end_time is calculated once, right here, before any worker starts —
    not inside worker.py — so every single virtual user is handed the
    exact same cutoff and none of them drift relative to each other.
    """
    end_time = time.perf_counter() + duration

    async with httpx.AsyncClient() as client:
        tasks = [
            run_virtual_user(client, url, timeout, end_time)
            for _ in range(users)
        ]
        results_per_user = await asyncio.gather(*tasks)

    all_results: list[RequestResult] = []
    for user_results in results_per_user:
        all_results.extend(user_results)

    return all_results

