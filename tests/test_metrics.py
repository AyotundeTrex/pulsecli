"""
Tests for app/metrics.py

These use hand-built RequestResult objects with known numbers, so the
expected values in each test are calculated by hand (shown in comments)
and checked against what the function actually returns. No network,
no mocking needed — this is pure arithmetic, which is exactly what
makes it easy to test completely.
"""

from app.http_client import RequestResult
from app.metrics import calculate_metrics
import pytest


def make_result(response_time: float, success: bool, status_code: int = 200) -> RequestResult:
    """Small helper so each test doesn't repeat every RequestResult field."""
    return RequestResult(
        timestamp="2026-01-01T00:00:00",
        response_time=response_time,
        status_code=status_code if success else None,
        success=success,
        error=None if success else "error",
    )


def test_all_successful_requests():
    # 3 requests: 0.1s, 0.2s, 0.3s -> avg=0.2, min=0.1, max=0.3
    results = [make_result(0.1, True), make_result(0.2, True), make_result(0.3, True)]
    m = calculate_metrics(results, elapsed_seconds=1.0)

    assert m.total_requests == 3
    assert m.successful == 3
    assert m.failed == 0
    assert m.avg_response_time == pytest.approx(0.2)
    assert m.min_response_time == 0.1
    assert m.max_response_time == 0.3
    assert m.requests_per_second == 3.0
    assert m.error_rate == 0.0


def test_mixed_success_and_failure():
    # 4 successful (0.1, 0.2, 0.3, 0.4) + 1 failed (1.0)
    # avg/min/max include ALL requests -> avg=0.4, min=0.1, max=1.0
    # error_rate = 1/5 * 100 = 20.0
    results = [
        make_result(0.1, True), make_result(0.2, True),
        make_result(0.3, True), make_result(0.4, True),
        make_result(1.0, False),
    ]
    m = calculate_metrics(results, elapsed_seconds=2.0)

    assert m.total_requests == 5
    assert m.successful == 4
    assert m.failed == 1
    assert abs(m.avg_response_time - 0.4) < 0.0001
    assert m.min_response_time == 0.1
    assert m.max_response_time == 1.0
    assert m.requests_per_second == 2.5
    assert m.error_rate == 20.0


def test_all_failed_requests():
    results = [make_result(0.5, False), make_result(0.6, False)]
    m = calculate_metrics(results, elapsed_seconds=1.0)

    assert m.total_requests == 2
    assert m.successful == 0
    assert m.failed == 2
    assert m.error_rate == 100.0


def test_empty_results_does_not_crash():
    """
    If a test somehow collects zero results (e.g. duration=0, or every
    virtual user crashed before completing a single request), the
    program must report zero/0.0 across the board instead of raising
    a ZeroDivisionError or a crash — a load test reporting "nothing
    happened" is a valid, real result, not a bug.
    """
    m = calculate_metrics([], elapsed_seconds=10.0)

    assert m.total_requests == 0
    assert m.successful == 0
    assert m.failed == 0
    assert m.avg_response_time == 0.0
    assert m.min_response_time == 0.0
    assert m.max_response_time == 0.0
    assert m.requests_per_second == 0.0
    assert m.error_rate == 0.0


def test_single_result():
    """Edge case: exactly one request. min, max, and avg should all be equal."""
    m = calculate_metrics([make_result(0.5, True)], elapsed_seconds=1.0)

    assert m.total_requests == 1
    assert m.avg_response_time == 0.5
    assert m.min_response_time == 0.5
    assert m.max_response_time == 0.5


def test_zero_elapsed_time_does_not_crash():
    """
    Guards against a division-by-zero if elapsed_seconds is ever 0 —
    shouldn't happen in normal use, but a metrics function should never
    crash on a weird input; it should degrade gracefully.
    """
    m = calculate_metrics([make_result(0.1, True)], elapsed_seconds=0.0)
    assert m.requests_per_second == 0.0

