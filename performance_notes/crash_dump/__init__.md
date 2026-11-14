# harness_designer/crash_dump/__init__.py

Facade: re-exports the capture API (`capturable`, `walk`, `dump_to_html`, the writer and the entry points). Importing it loads the schema, registry, walker, render and writer modules (not the `extras/` ones, which `render.py` imports lazily only when it meets a value of that type). Import cost only; nothing here runs per frame. A crash dump itself is a rare event, so its cost matters only if a dump is triggered in a loop (see `crash_dump/entrypoints.md`).
