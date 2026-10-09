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

## Added in the folder review: `register` and `release`
`register` runs only when a wire's point list changes shape. A plain waypoint move needs no call, because the vertices reference the live Point buffers, so this is already the cheap design. `release` drops vertex references on wire deletion and is not a concern.

