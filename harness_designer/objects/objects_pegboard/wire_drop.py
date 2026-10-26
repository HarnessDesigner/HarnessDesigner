# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dropping a wire from a peg-board wire table onto another floating panel.

Both panels are GL textures drawn by canvas-level objects, not real widgets on
screen, so Qt's own drag and drop (which needs a real window to run its loop
in) cannot carry the drag. ``objects_pegboard.table.Table`` recognises the drag
of a wire row itself and, while it lasts, asks this module which target is
under the pointer; a target announces itself by calling :func:`register`.

A target is any object with these methods (today only
``objects_pegboard.section.Section``, the concentric section widget):

- ``wire_drop_contains(screen_pos)`` -- whether the pointer is over it (it is
  visible and the logical canvas pixel is inside its rectangle);
- ``set_wire_drop_hover(flag)`` -- show / hide its "a wire can be dropped here"
  highlight;
- ``accept_wire_drop(wire_id)`` -- take the wire, returning whether anything
  changed;
- ``render_id`` -- the stacking order, so the topmost of overlapping targets wins.

This module only finds the target; it is in its own file because ``Table`` and
``Section`` import each other's constants and may not import each other.
"""

from typing import TYPE_CHECKING, Union as _Union

import weakref

from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import section as _section
    from ...geometry import point as _point


_targets: "weakref.WeakSet[_section.Section]" = weakref.WeakSet()


@_check_types.do
def register(target: "_section.Section") -> None:
    """Make *target* a place a wire can be dropped. Held weakly."""
    _targets.add(target)


@_check_types.do
def unregister(target: "_section.Section") -> None:
    """*target* can no longer take a drop."""
    _targets.discard(target)


@_check_types.do
def target_at(screen_pos: "_point.Point") -> _Union["_section.Section", None]:
    """The topmost target under *screen_pos* (logical canvas pixels), or ``None``."""
    best = None

    for target in _targets:
        if not target.wire_drop_contains(screen_pos):
            continue

        if best is None or target.render_id > best.render_id:
            best = target

    return best
