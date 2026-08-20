"""
Takes the calculated metrics and prints them as a clean, readable report.
"""

from app.config import Config
from app.metrics import Metrics


def format_report(config: Config, metrics: Metrics) -> str:
    """
    Build the final "LOAD TEST RESULTS" summary as a single string.

    This file's only job is turning already-correct numbers into
    readable text — it does no calculation itself. That separation
    from metrics.py means if you ever want a different output format
    later (JSON, CSV, a web page), you write a new function here
    without touching the arithmetic that's already been verified.
    """
    lines = [
        "LOAD TEST RESULTS",
        "",
        f"Target: {config.url}",
        f"Virtual Users: {config.users}",
        f"Duration: {config.duration} seconds",
        "",
        f"Total Requests: {metrics.total_requests}",
        f"Successful: {metrics.successful}",
        f"Failed: {metrics.failed}",
        "",
        f"Average Response Time: {metrics.avg_response_time:.2f}s",
        f"Minimum Response Time: {metrics.min_response_time:.2f}s",
        f"Maximum Response Time: {metrics.max_response_time:.2f}s",
        "",
        f"Requests/sec: {metrics.requests_per_second:.1f}",
        f"Error Rate: {metrics.error_rate:.2f}%",
    ]
    return "\n".join(lines)

