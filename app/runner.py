"""
Coordinates the whole test run.

This is the "conductor" — it doesn't send requests itself, it starts the
right number of virtual users at the same time (concurrently), lets them
run for the configured duration, and then collects their results.

Responsibilities (implemented in Stage 4):
- Create `users` virtual users, all running concurrently via asyncio
- Let them run until `duration` seconds have passed
- Gather every request result from every virtual user into one place

Left empty on purpose for Stage 1.
"""
