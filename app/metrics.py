"""
Turns a pile of individual request results into the summary numbers
a human actually cares about.
"""

from dataclasses import dataclass

from app.http_client import RequestResult


@dataclass
class Metrics:
    """
    The final aggregate numbers for one test run — this is what
    reporter.py (Stage 6) will format into the "LOAD TEST RESULTS"
    summary block.
    """
    total_requests: int
    successful: int
    failed: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float


def calculate_metrics(results: list[RequestResult], elapsed_seconds: float) -> Metrics:
    """
    Turn a raw list of RequestResults into the aggregate Metrics above.

    Why `elapsed_seconds` is the ACTUAL measured wall-clock time of the
    whole test, not just the --duration the user asked for: workers
    stop checking the cutoff *before* starting a new request, but a
    request already in flight when the cutoff hits still finishes.
    That means the real test almost always runs a few hundred
    milliseconds longer than the requested duration. Using the
    honestly-measured time for requests-per-second, instead of the
    requested number, is the more accurate (and more honest) number —
    this is the same instinct as using time.perf_counter() instead of
    time.time() back in http_client.py: measure what actually
    happened, not what was merely asked for.

    Why error_rate is (failed / total) * 100: it's a percentage of ALL
    requests, not a ratio of failed-to-successful. A 1.11% error rate
    means "out of every request sent, about 1 in 90 failed" — that's
    the number that tells you how reliable the target was under load.

    Why min/max/avg matter together, not just avg alone: average alone
    can hide problems. If 99 requests take 0.1s and 1 request takes
    9s, the average looks fine (~0.19s) but that one request represents
    a real user having a bad experience. min and max at least show you
    the full spread, even without going as far as percentiles.
    """
    total = len(results)

    if total == 0:
        return Metrics(
            total_requests=0, successful=0, failed=0,
            avg_response_time=0.0, min_response_time=0.0, max_response_time=0.0,
            requests_per_second=0.0, error_rate=0.0,
        )

    successful = sum(1 for r in results if r.success)
    failed = total - successful

    response_times = [r.response_time for r in results]
    avg_response_time = sum(response_times) / total
    min_response_time = min(response_times)
    max_response_time = max(response_times)

    requests_per_second = total / elapsed_seconds if elapsed_seconds > 0 else 0.0
    error_rate = (failed / total) * 100

    return Metrics(
        total_requests=total,
        successful=successful,
        failed=failed,
        avg_response_time=avg_response_time,
        min_response_time=min_response_time,
        max_response_time=max_response_time,
        requests_per_second=requests_per_second,
        error_rate=error_rate,
    )

