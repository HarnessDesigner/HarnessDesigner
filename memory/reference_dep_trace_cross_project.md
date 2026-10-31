---
name: reference-dep-trace-cross-project
description: dep_trace.py can be pointed at any Python project, not just harness_designer itself
metadata:
  type: reference
---

`diagnostics/dep_trace.py` (in the harness_designer repo) is a generic, project-agnostic
AST analysis tool. It can be run with `target` set to a directory in a completely unrelated
repo (e.g. `C:\Users\drsch\PycharmProjects\vector_dbc`), not only paths under harness_designer.

**How to apply:** When doing cross-project work from a harness_designer session (e.g. porting
or analyzing another one of the user's Python projects), prefer
`python diagnostics/dep_trace.py <other_project_dir> [--types|--calls|--overrides|--imported-by] [--name PATTERN]`
over manual Grep/Read for "where is X defined/used/called" questions, exactly as CLAUDE.md
recommends for harness_designer itself. Confirmed by the user directly (2026-10-08).
