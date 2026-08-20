"""
Tests for app/config.py

Covers: Config.validate() catching bad input, load_config_file()
handling missing/malformed files, and build_config()'s merge rule
(command-line arguments must override config file values).
"""

import json

import pytest

from app.config import Config, build_config, load_config_file
from app.exceptions import ConfigError


# ---- Config.validate() ----

def test_valid_config_passes():
    config = Config(url="https://example.com", users=10, duration=30, timeout=10.0, method="GET")
    config.validate()  # should not raise


def test_missing_url_raises():
    config = Config(url="", users=10, duration=30, timeout=10.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_url_without_scheme_raises():
    config = Config(url="example.com", users=10, duration=30, timeout=10.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_negative_users_raises():
    config = Config(url="https://example.com", users=-5, duration=30, timeout=10.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_zero_users_raises():
    config = Config(url="https://example.com", users=0, duration=30, timeout=10.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_negative_duration_raises():
    config = Config(url="https://example.com", users=10, duration=-1, timeout=10.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_negative_timeout_raises():
    config = Config(url="https://example.com", users=10, duration=30, timeout=-1.0, method="GET")
    with pytest.raises(ConfigError):
        config.validate()


def test_non_get_method_raises():
    """Version 1 only supports GET — anything else should fail clearly."""
    config = Config(url="https://example.com", users=10, duration=30, timeout=10.0, method="POST")
    with pytest.raises(ConfigError):
        config.validate()


# ---- load_config_file() ----

def test_load_valid_config_file(tmp_path):
    """
    tmp_path is a built-in pytest fixture: it hands us a real, temporary
    directory that pytest automatically cleans up after the test. This
    lets us test real file-reading behavior without touching any actual
    file in the project or leaving junk files behind.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"url": "https://example.com", "users": 5}))

    result = load_config_file(str(config_file))
    assert result["url"] == "https://example.com"
    assert result["users"] == 5


def test_load_missing_file_raises():
    with pytest.raises(ConfigError):
        load_config_file("this_file_does_not_exist.json")


def test_load_malformed_json_raises(tmp_path):
    config_file = tmp_path / "bad_config.json"
    config_file.write_text("{ this is not valid json")

    with pytest.raises(ConfigError):
        load_config_file(str(config_file))


# ---- build_config() merge precedence ----

def test_cli_args_override_config_file(tmp_path):
    """
    This is the precedence rule agreed on back when the config system
    was designed: command-line flags always win over the config file.
    The file supplies defaults; the CLI overrides them. This test exists
    specifically to catch a regression if that rule ever silently flips.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"url": "https://example.com", "users": 10}))

    cli_args = {"url": None, "users": 999, "duration": None, "timeout": None, "method": None}
    config = build_config(cli_args, config_file_path=str(config_file))

    assert config.users == 999  # CLI value wins
    assert config.url == "https://example.com"  # falls back to file value


def test_build_config_without_file_uses_cli_only():
    cli_args = {"url": "https://example.com", "users": 20, "duration": 15, "timeout": 5.0, "method": "GET"}
    config = build_config(cli_args, config_file_path=None)

    assert config.url == "https://example.com"
    assert config.users == 20
    assert config.duration == 15


def test_build_config_missing_url_raises():
    cli_args = {"url": None, "users": 10, "duration": 30, "timeout": None, "method": None}
    with pytest.raises(ConfigError):
        build_config(cli_args, config_file_path=None)

