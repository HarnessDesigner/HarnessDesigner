# harness_designer/ui/prop_ctrls/__init__.py

Facade: imports all of the property-control modules (about 28) and re-exports their classes. No per-call cost. Importing it loads every control type at startup even if a project never shows that property, which is a one-time import cost. The controls themselves are built lazily per tab (see `LazyTabMixin`), which is where the real saving is.
