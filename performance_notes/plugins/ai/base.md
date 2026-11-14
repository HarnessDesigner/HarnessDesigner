# harness_designer/plugins/ai/base.py

AIBase — the base a concrete backend subclasses, *alongside* Plugin (never through it — see ../plugin.py's _PluginMeta adjacency requirement, which an abstract intermediate base like this can't satisfy; a concrete backend combines both via multiple inheritance, e.g. class ClaudePlugin(AIBase, Plugin): ..., with start_registration() called immediately before that one class statement).

Nested loops (cost grows with the product of the sizes; check the sizes are small): `AIBase._session_loop` (lines 62-85, depth 2).

Status: static read of the code only. Nothing here has been profiled.
