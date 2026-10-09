"""Pseudo ``PJTBundleLayout`` row for an in-memory bundle waypoint.

Mirrors :mod:`.pseudo_wire_layout` (``PseudoPJTWireLayout``) -- the two row
types are structurally near-identical, so this is the same pattern: a real
``PJTBundleLayout`` subclass that never touches the database. Its positions
and visibility come from :meth:`PseudoPJTBundleLayout.configure` and live
only in memory.

Used while a peg-board drag needs a waypoint that does not have a real row
yet. The drag creates these, shows them, and the real rows are written only
when the drag releases.

Unlike the wire probe version, visibility is configurable: a drag waypoint
is meant to be seen, whereas a snap probe must stay hidden.
"""

from typing import TYPE_CHECKING, Union as _Union

from .pjt_bundle_layout import PJTBundleLayout
from ...geometry import point as _point


if TYPE_CHECKING:
    from ...database.global_db import bundle_cover as _global_bundle_cover


class _PseudoAttachedBundle:
    """Stand-in for a ``PJTBundle`` row, exposing only what a bundle layout's
    marker reads from ``attached_bundles()[0]``: ``.part`` (the cover part, for
    sizing and colour), ``.part_id``, and ``.diameter``.
    """
    __slots__ = ('part', 'part_id', 'diameter')

    def __init__(
        self, part: "_global_bundle_cover.BundleCover", diameter: float
    ) -> None:
        self.part = part
        self.part_id = part.db_id
        self.diameter = diameter


class PseudoPJTBundleLayout(PJTBundleLayout):
    """Pseudo ``PJTBundleLayout`` row for an in-memory bundle waypoint.

    Constructed directly with ``table=None`` and a throwaway ``db_id``, never
    through ``PJTBundleLayoutsTable``. Every database-backed property is
    overridden to return in-memory state set by :meth:`configure`. Setters are
    no-ops, so nothing is written back to the database.
    """

    _table = None

    _position3d: _point.Point | None = None
    _position_pegboard: _point.Point | None = None
    _bundle_part: _Union["_global_bundle_cover.BundleCover", None] = None
    _bundle_diameter: float = 0.0
    _visible_pegboard: bool = True

    def configure(
        self,
        bundle_part: "_global_bundle_cover.BundleCover | None" = None,
        bundle_diameter: float = 0.0,
        position3d: _point.Point | None = None,
        position_pegboard: _point.Point | None = None,
        visible_pegboard: bool = True,
    ) -> None:
        self._bundle_part = bundle_part
        self._bundle_diameter = bundle_diameter
        self._position3d = position3d
        self._position_pegboard = position_pegboard
        self._visible_pegboard = visible_pegboard

    @property
    def attached_bundles(self) -> list:
        if self._bundle_part is None:
            return []

        return [_PseudoAttachedBundle(self._bundle_part, self._bundle_diameter)]

    @property
    def diameter(self) -> float:
        return self._bundle_diameter

    @property
    def table(self) -> None:
        return None

    def delete(self) -> None:
        # No real row backs this instance -- the drag tears these down itself.
        pass

    def get_object(self) -> None:
        return None

    def set_object(self, obj: object) -> None:
        pass

    @property
    def position3d(self) -> _point.Point | None:
        return self._position3d

    @property
    def position3d_id(self) -> bytes | None:
        if self._position3d is None:
            return None

        db_id = self._position3d.db_id
        return db_id[:-2] if db_id is not None else None

    @position3d_id.setter
    def position3d_id(self, value: bytes | None) -> None:
        pass

    @property
    def position_pegboard(self) -> _point.Point | None:
        return self._position_pegboard

    @property
    def position_pegboard_id(self) -> bytes | None:
        if self._position_pegboard is None:
            return None

        db_id = self._position_pegboard.db_id
        return db_id[:-2] if db_id is not None else None

    @position_pegboard_id.setter
    def position_pegboard_id(self, value: bytes | None) -> None:
        pass

    @property
    def is_visible3d(self) -> bool:
        return False

    @is_visible3d.setter
    def is_visible3d(self, value: bool) -> None:
        pass

    @property
    def is_visible_pegboard(self) -> bool:
        return self._visible_pegboard

    @is_visible_pegboard.setter
    def is_visible_pegboard(self, value: bool) -> None:
        # Memory only: the object-level visibility is what the renderer reads,
        # and it must not write a database row mid-drag.
        self._visible_pegboard = bool(value)

    @property
    def smooth(self) -> bool | None:
        return True

    @smooth.setter
    def smooth(self, value: bool | None) -> None:
        pass
