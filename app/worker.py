"""
Simulates ONE virtual user.

A "virtual user" is one simulated visitor: it repeatedly sends requests
to the target until the test duration runs out, and records the result
of every single request it makes.

Responsibilities (implemented in Stage 4):
- Loop: send a request via http_client, record the result, repeat
- Stop looping once the test duration has elapsed
- Hand off every individual result to the metrics collector

Left empty on purpose for Stage 1.
"""
