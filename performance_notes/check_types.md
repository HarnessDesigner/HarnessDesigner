# harness_designer/check_types.py

## Line 224-225 — needs investigation, not a performance item
`do(func)` returns `func` unconditionally as its very first statement, before
the `_FROZEN` check and before building `_wrapper`. Every line after it
(227-275) is unreachable dead code. This means `@_check_types.do` — applied
at roughly 6179 call sites across the package per MEMORY.md — currently adds
zero wrapper/runtime overhead anywhere, since decoration is a no-op that
returns the original function unchanged.

This is flagged here only because it directly bears on whether the decorator
is a performance concern elsewhere in the codebase (it is not, as currently
written). Whether the early `return func` is intentional (e.g. temporarily
disabled while profiling) or a forgotten leftover is a functional question,
not a formatting one, so the source was left unmodified — worth confirming
with the user directly.
