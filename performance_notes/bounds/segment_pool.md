# harness_designer/bounds/segment_pool.py

## Line 165 (`segments`) — full vertex re-stack on every call
`vertices = np.stack(self._buffers)[:, [0, 2]]` rebuilds the entire vertex
array (every live wire vertex, one `np.stack` call over the whole
`_buffers` list) from scratch on every single `segments()` call, with no
caching between calls. Per the module docstring, `segments()` is what
`wire_routing/routing.py`'s wire-to-wire lane check reads -- if that check
runs per route computation during interactive drag/reroute (not confirmed,
needs checking against `wire_routing/routing.py`/`reroute.py`), this is a
recurring full-rebuild on a path that's plausibly hot during interactive
wire editing. `CODEBASE_MAP.md`/git history mark this pooled design as
freshly finished (2026-09), so this may already be within acceptable
bounds -- flagging for a benchmark against a project with many wires/
waypoints before assuming it needs a cache.
