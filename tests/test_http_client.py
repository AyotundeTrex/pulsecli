"""
Tests for app/http_client.py

Uses mocked HTTP responses instead of real websites, per project
requirements — these tests must pass with no network connection at
all, and must never depend on some third-party site staying online.
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.http_client import send_request


@pytest.mark.asyncio
async def test_successful_request():
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    client.get = AsyncMock(return_value=mock_response)

    result = await send_request(client, "https://example.com", timeout=10)

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    assert result.response_time >= 0


@pytest.mark.asyncio
async def test_timeout_is_recorded_not_raised():
    """
    A timeout must come back as a normal RequestResult with
    success=False — it must NOT bubble up as an uncaught exception.
    A load test that crashes on the first timeout would be useless,
    since timeouts under load are exactly what we're testing for.
    """
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    result = await send_request(client, "https://example.com", timeout=1)

    assert result.success is False
    assert result.status_code is None
    assert result.error is not None


@pytest.mark.asyncio
async def test_connection_error_is_recorded_not_raised():
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    result = await send_request(client, "https://example.com", timeout=10)

    assert result.success is False
    assert result.status_code is None
    assert result.error is not None


@pytest.mark.asyncio
async def test_http_500_counts_as_failure():
    """
    The network layer succeeding (we got a response) is different from
    the request succeeding (the server did what we wanted). A 500
    response is a real failure for load-testing purposes even though
    no exception was raised.
    """
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    client.get = AsyncMock(return_value=mock_response)

    result = await send_request(client, "https://example.com", timeout=10)

    assert result.success is False
    assert result.status_code == 500


@pytest.mark.asyncio
async def test_http_404_counts_as_failure():
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 404
    client.get = AsyncMock(return_value=mock_response)

    result = await send_request(client, "https://example.com", timeout=10)

    assert result.success is False
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_result_has_a_timestamp():
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    client.get = AsyncMock(return_value=mock_response)

    result = await send_request(client, "https://example.com", timeout=10)

    assert result.timestamp is not None

