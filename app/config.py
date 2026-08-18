"""
Holds the settings for a single load test run — the target URL, how many
virtual users to simulate, how long to run, the timeout per request, etc.

Responsibilities (implemented in Stage 2):
- Define a Config dataclass (url, users, duration, timeout, method)
- Validate that values make sense (e.g. users > 0, url is well-formed)
- Merge command-line arguments with an optional JSON config file

Left empty on purpose for Stage 1.
"""
