"""
Custom error types, so the rest of the code can tell the difference
between "something is wrong with how the test was configured" (stop
before starting) and "one request failed" (just count it as a failure
and keep going).
"""


class ConfigError(Exception):
    """
    Raised when the test configuration is invalid — a missing URL,
    a negative number of users, a duration of zero, etc.

    This is deliberately a *different* exception type from a normal
    Python error. It lets cli.py catch configuration problems
    specifically and print a clean, human-readable message instead of
    a raw Python traceback that a beginner (or anyone in a hurry)
    would find intimidating.
    """
    pass


class RequestExecutionError(Exception):
    """
    Raised internally when a single HTTP request fails in a way worth
    distinguishing from a normal "the server returned an error"
    result. Used by http_client.py, implemented in Stage 3.
    """
    pass

