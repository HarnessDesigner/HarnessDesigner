# harness_designer/shapes/__init__.py

## Line 36-149 (`cache_primitives`) — builds every primitive once, with timing
Builds each primitive's mesh and caches it, reporting progress to a splash screen when one is given. Runs once at start-up. The `_timed` wrapper logs how long each step takes.
