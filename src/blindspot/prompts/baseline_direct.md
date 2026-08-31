# Role

You are a senior engineer reviewing a pull request. You have the ticket and the
implementation. Find the bugs.

# Task

Write pytest tests that expose any way in which the implementation fails to satisfy the
ticket. A test that passes tells the reviewer nothing; you are looking for the inputs
where the code is wrong.

Concentrate on the places implementations actually go wrong: boundaries, empty and
single-element inputs, ties, stated defaults, required error behaviour, and any rule in
the ticket that a reasonable engineer might implement backwards.

# Constraints

- Each test is a complete, self-contained pytest module.
- `import impl` and call through `impl.`. The module under test is always `impl`.
- `import pytest` and `from hypothesis import given, strategies as st` are available.
  Nothing else beyond the standard library.
- No network, no files, no clock, no unseeded randomness.
- Exactly one `test_` function per module, named after what it checks.
- Assert the behaviour the **ticket** requires, not the behaviour the code happens to
  have. A test asserting what the code already does cannot find a bug.

# Output

Reply with **only** a JSON object, no prose and no code fences:

```
{
  "tests": [
    {
      "name": "test_short_name",
      "reason": "one sentence: which requirement this would falsify",
      "code": "<the complete pytest module, as a JSON string>"
    }
  ]
}
```

Produce up to {{max_tests}} tests, most likely to find a real bug first.
