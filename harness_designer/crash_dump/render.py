"""Per-type rendering: how to label/format a captured value, and what
counts as its children -- independent of, and consulted only after, the
capture-schema registry (``registry.py``) has already decided a value is
NOT itself a walkable, schema'd app object (those stay refs, handled
entirely by the walker).

Two tiers, both reached through the single ``iter_render_children``
dispatch function:

- True builtins (``dict``/``list``/``tuple``/``set``/``frozenset``) and
  app-authored custom types are registered with real
  ``functools.singledispatch`` -- zero import cost for the builtins, and
  the app already owns the import for its own types, so registering one
  here (``@iter_render_children.register(MyType)``) costs nothing extra.
- The library's own shipped support for optional stdlib/third-party
  "extras" (``decimal.Decimal``, ``uuid.UUID``, ``datetime.datetime``,
  numpy, ...) is resolved lazily by a string key
  (``f'{module}.{qualname}'``) against ``crash_dump.extras`` submodules,
  so importing ``crash_dump`` never forces importing a module the host
  app doesn't otherwise use.

A renderer returns one of:
  - ``('value', json_safe_scalar)`` -- a terminal, already-formatted value.
  - ``('children', [(name, child_value), ...])`` -- a breakdown to recurse
    into; each child is fed back through the walker's own classification,
    so a child that happens to itself be a walkable app object still
    becomes a ``ref`` rather than being inlined here.
  - ``None`` -- this type isn't covered; the caller omits it entirely.
"""
from __future__ import annotations

import importlib
from functools import singledispatch

from .. import check_types as _check_types

_LAZY_EXTRAS = {
    'decimal.Decimal': 'harness_designer.crash_dump.extras.decimal_support',
    'uuid.UUID': 'harness_designer.crash_dump.extras.uuid_support',
    'datetime.datetime': 'harness_designer.crash_dump.extras.datetime_support',
    'datetime.date': 'harness_designer.crash_dump.extras.datetime_support',
    'numpy.ndarray': 'harness_designer.crash_dump.extras.numpy_support',
}
_resolved_extras: dict[str, object] = {}


@_check_types.do
def _resolve_extra(type_key: str):
    cached_renderer = _resolved_extras.get(type_key)
    if cached_renderer is not None:
        return cached_renderer
    module_path = _LAZY_EXTRAS.get(type_key)
    if module_path is None:
        return None
    extras_module = importlib.import_module(module_path)
    resolved_renderer = extras_module.render
    _resolved_extras[type_key] = resolved_renderer
    return resolved_renderer


@singledispatch
@_check_types.do
def iter_render_children(value):
    type_key = f'{type(value).__module__}.{type(value).__qualname__}'
    renderer = _resolve_extra(type_key)
    if renderer is None:
        return None
    return renderer(value)


@iter_render_children.register(list)
@iter_render_children.register(tuple)
@iter_render_children.register(set)
@iter_render_children.register(frozenset)
@_check_types.do
def _render_sequence(value):
    return ('children', [(f'[{index}]', item) for index, item in enumerate(value)])


@_check_types.do
def _key_label(key) -> str:
    if isinstance(key, bytes):
        return key.hex()
    return str(key)


@iter_render_children.register(dict)
@_check_types.do
def _render_mapping(value):
    return ('children', [(_key_label(key), item) for key, item in value.items()])
