# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
External, class-keyed registry of dump capture groups.

``@capturable`` never mutates the class it decorates -- classes in this app
are Cython-compiled (pure-Python mode), and reads of a class attribute are
always safe regardless. All cascade/override/merge work happens once, at
decoration time, so a dump-time lookup is a single MRO walk with no merge
work left to do.

Every ``cls``/``source_class`` parameter in this module is annotated
``object``, not ``type``, on purpose: Cython's pure-Python-mode ArgTypeTest
for a bare builtin ``type`` annotation rejects any *subclass* of ``type``
(e.g. a custom metaclass like ``PointMeta``), so decorating a class whose
metaclass isn't exactly ``type`` crashes a compiled build at import time.

A registered class's entry is a tuple of ``CaptureGroup``s, one per class in
its hierarchy that actually declared something (its own ``__dump_schema__``
and/or its own ``@dump_property``-tagged properties). Each group keeps the
severity its source class resolved for itself at that source class's own
decoration time -- a subclass's severity only ever gates what the subclass
itself added or explicitly overrode, never what an ancestor contributed.

Groups are treated as immutable and may be shared, by reference, across
every descendant that inherits them unchanged. A subclass that overrides an
inherited name never mutates the ancestor's stored group (other, unrelated
descendants still hold a reference to it) -- it copies just that one group,
with the overridden name filtered out, into its own registry entry.
"""

from __future__ import annotations

from .schema import Attr
from .. import check_types as _check_types


_registry: dict[type, tuple['CaptureGroup', ...]] = {}


class CaptureGroup:
    __slots__ = ('source_class', 'severity', 'attrs')

    @_check_types.do
    def __init__(self, source_class: object,
                 severity: int, attrs: tuple[Attr, ...]):

        self.source_class = source_class
        self.severity = severity
        self.attrs = attrs

    @_check_types.do
    def __repr__(self) -> str:
        return (f'CaptureGroup({self.source_class.__name__}, '
                f'severity={self.severity}, attrs={self.attrs!r})')


@_check_types.do
def _own_dump_property_attrs(cls: object) -> list[Attr]:
    found: list[Attr] = []
    for name, value in vars(cls).items():
        if not isinstance(value, property) or value.fget is None:
            continue

        tagged_severity = getattr(value.fget, '_dump_severity', None)
        if tagged_severity is None:
            continue

        found.append(Attr(name, tagged_severity))

    return found


@_check_types.do
def _resolve_own_severity(cls: object, explicit_severity: int | None) -> int:
    if explicit_severity is not None:
        return explicit_severity

    for ancestor in cls.__mro__[1:]:  # NOQA
        ancestor_groups = _registry.get(ancestor)
        if ancestor_groups is None:
            continue

        for group in ancestor_groups:
            if group.source_class is ancestor:
                return group.severity

    return 1


def capturable(*, severity: int | None = None):
    """
    Class decorator: read ``__dump_schema__`` (if defined directly on
    this class) and any ``@dump_property``-tagged properties defined
    directly on this class, cascade in every already-registered ancestor's
    capture groups (deduplicated by source class, for multiple
    inheritance), apply this class's own entries as overrides wherever a
    name collides with an inherited one, and store the result in the
    module-level registry under this exact class object.

    ``severity`` is this class's own gate: explicit, else inherited from
    the nearest already-decorated ancestor, else ``1``.
    """

    def decorator(cls: object) -> object:
        own_severity = _resolve_own_severity(cls, severity)

        raw_entries: dict[str, Attr] = {}
        for attr in _own_dump_property_attrs(cls):
            raw_entries[attr.name] = attr

        for attr in vars(cls).get('__dump_schema__', ()):
            raw_entries[attr.name] = attr

        inherited_groups: list[CaptureGroup] = []
        seen_sources: set[type] = set()
        for ancestor in cls.__mro__[1:]:  # NOQA
            ancestor_groups = _registry.get(ancestor)
            if ancestor_groups is None:
                continue

            for group in ancestor_groups:
                if group.source_class in seen_sources:
                    continue

                seen_sources.add(group.source_class)
                inherited_groups.append(group)

        final_inherited_groups: list[CaptureGroup] = []
        for group in inherited_groups:
            collides = any(attr.name in raw_entries for attr in group.attrs)
            if not collides:
                final_inherited_groups.append(group)
                continue

            kept_attrs = tuple(attr for attr in group.attrs
                               if attr.name not in raw_entries)

            final_inherited_groups.append(
                CaptureGroup(group.source_class, group.severity, kept_attrs))

        own_group = CaptureGroup(cls, own_severity, tuple(raw_entries.values()))
        _registry[cls] = (own_group,) + tuple(final_inherited_groups)

        return cls

    return decorator


@_check_types.do
def capture_groups_for(cls: object) -> tuple[CaptureGroup, ...] | None:
    """
    The full, already-merged set of capture groups for ``cls`` -- itself
    if registered, else its nearest registered ancestor. ``None`` if
    nothing in ``cls``'s MRO was ever decorated (not registered == not
    dumped).
    """

    for candidate in cls.__mro__:  # NOQA
        groups = _registry.get(candidate)
        if groups is not None:
            return groups
