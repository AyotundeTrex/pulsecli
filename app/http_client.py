"""
Sends a single HTTP request and reports back what happened.

This is the smallest building block in the whole tool — everything else
(virtual users, concurrency, metrics) is built on top of "send one request,
time it, record whether it succeeded."

Responsibilities (implemented in Stage 3):
- Send one async GET request using httpx
- Measure how long it took (response time)
- Catch timeouts and connection errors without crashing the program
- Return a structured result (status code, response time, success/failure)

Left empty on purpose for Stage 1.
"""
