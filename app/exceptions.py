"""
Custom error types, so the rest of the code can tell the difference
between "something is wrong with how the test was configured" (stop
before starting) and "one request failed" (just count it as a failure
and keep going).

Responsibilities (implemented in Stage 2/3):
- ConfigError — raised when the CLI args or config file don't make sense
- RequestExecutionError — raised internally when a single request fails
  in a way worth distinguishing (used by http_client.py)

Left empty on purpose for Stage 1.
"""
