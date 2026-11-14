# harness_designer/handlers/bundle_wire_model.py

Pure-geometry model of one wire through one bundle: `BundleModel`, `WireModel`, `Assembly.plan(held)` -> `MovePlan`. Standard library only: points are `(x, z)` tuples and the helpers (`_sub`, `_add`, `_scale`, `dist`, `_unit`, `_toward`) are plain function calls on tuples. That follows MEMORY.md's rule for hot paths with many tiny operations (plain Python rather than NumPy), and it is why this module needs no performance changes.

## Line 174-309 (`Assembly.plan`) — a fixed sequence of steps, no search
One pass through a short fixed sequence (slide slack, pull the opposite end, drag the bundle, clamp) with a few helper closures, so cost is a few dozen tuple operations. It is called from `rope_pull_handler._evaluate_points` (`eval_bundle_wire`) once per wire-in-bundle per evaluation. With the 18-evaluation search in `resolve_rigid_move` (see `rope_pull_handler.md`) that is up to 18 plans per bundle wire per mouse move; each is microseconds, so the module itself is not the cost, the number of evaluations is.

## Line 136-139 (`MovePlan.describe`)
Builds f-strings for the debug trace. Only called from `_trace` lambdas, which do not run unless tracing is on.
