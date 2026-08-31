# Role

You are the same engineer who just implemented this ticket, now writing the test suite
that will ship alongside your implementation. Your reviewer expects thorough tests before
they approve the pull request.

# Task

Write a pytest suite for the implementation below. Cover the normal path, the edge cases
you think matter, and the error behaviour the ticket describes. Aim for the kind of
coverage that would let you approve this change with confidence.

# Constraints

- A single self-contained pytest module.
- `import impl` and call the public function(s) through `impl.`.
- `import pytest` is allowed. Nothing else outside the standard library.
- No network, no filesystem, no clock, no randomness.
- Every test must be deterministic.
- Use plain `assert`. Use `pytest.raises` for error cases.
- Between 8 and 20 test functions.

# Output format

Reply with **only** a JSON object, no prose and no code fences:

```
{"code": "<the complete contents of the test module, as a JSON string>"}
```
