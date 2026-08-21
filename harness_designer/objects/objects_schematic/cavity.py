# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import build123d
import numpy as np

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import text as _text
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


Config = _config.Config.editor_schematic


class Cavity(_base_schematic.BaseSchematic):
    """
    2D representation of a cavity for schematic view

    Renders only this cavity's own name -- RIGHT/BOTTOM-aligned text
    sitting just outside its owning housing's rectangle, a fixed gap
    above its terminal's own bracket. Its ``Text`` label (see
    ``shapes/text.py``) IS this object's own ``_vbo`` -- ``Text``
    implements the same public interface a real VBO handler does (see
    its own "VBOHandlerBase-compatible interface" section), so this
    class needs no ``render()``/``_compute_obb``/... override for
    rendering itself -- the standard inherited ``BaseVar`` pipeline
    drives it directly, matching how ``Base3D`` subclasses render.
    ``_compute_obb``/``_compute_aabb`` ARE still overridden here, since
    a Text's own "local" bounds aren't meaningful the way a real mesh's
    are (see Text's own docstring) -- real bounds come from its
    measured ``width``/``height`` instead.

    ``position2d``/``angle2d`` are computed and persisted by the owning
    ``objects_schematic/housing.py``'s ``Housing`` whenever its layout changes
    (see ``Housing._layout_children``) -- :meth:`_sync_vbo_transform`
    is what pushes that (RIGHT/BOTTOM-anchored) transform into the
    ``Text`` label itself, since ``Text`` has no reactive binding of
    its own the way a bound ``Point``/``Angle`` does.

    Owns two DB binds on itself: its own ``'name'`` (rebuilds this
    cavity's own text mesh, and tells the housing to update its cached
    copy -- see :meth:`_on_name_changed`) and the synthetic
    ``'terminal_id'`` tag (tells the housing to reposition this
    cavity's seated terminal -- see :meth:`_on_terminal_changed`). The
    housing itself binds to neither; both flow from here instead.
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    @_check_types.do
    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        self.db_obj = db_obj

        position = db_obj.position2d
        angle = db_obj.angle2d
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            vbo = self._build_vbo(db_obj.name)
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)
            self._sync_vbo_transform()

        self._name_cb = self.db_obj.bind(self._on_name_changed, 'name')

        # Fires whenever a terminal is attached, detached, or moved
        # to/from this cavity -- see database/project_db/pjt_terminal.py's
        # PJTTerminal.cavity_id setter, which is what actually calls
        # _populate('terminal_id') on this cavity's own db_obj (there's
        # no real terminal_id column on pjt_cavities to bind to
        # directly, so the terminal's own setter fires it by hand).
        self._terminal_cb = self.db_obj.bind(self._on_terminal_changed, 'terminal_id')

    @property
    @_check_types.do
    def housing(self):
        """This cavity's owning ``Housing2D``, or ``None``.

        Resolved on demand via ``self.parent.housing`` (see
        ``objects/cavity.py``'s ``Cavity``) rather than cached -- by the
        time either bound callback below fires, this cavity's housing
        is guaranteed to already exist (never at this object's own
        construction time).
        """
        housing_obj = self.parent.housing
        if housing_obj is None:
            return None

        return housing_obj.objschematic

    @_check_types.do
    def _on_name_changed(self, _entry=None):
        """Rebuild this cavity's own name mesh (see :meth:`_rebuild`)
        and tell the owning housing to update its cached copy -- a
        cavity rename can reorder its own slot and change the
        housing-wide max-cavity-name-width, so the housing does a full
        rebuild (see ``objects_schematic/housing.py``'s ``Housing.
        update_cavity_name``).
        """
        self._rebuild()

        housing = self.housing
        if housing is not None:
            housing.update_cavity_name(self.db_obj.db_id, self.db_obj.name)

    @_check_types.do
    def _on_terminal_changed(self, _entry=None):
        """Tell the owning housing to (re)position this cavity's own
        seated terminal -- see ``objects_schematic/housing.py``'s ``Housing.
        update_terminal_name``. Never a full housing rebuild -- seating
        a terminal doesn't affect sort order or the housing's own
        layout constants, only whether this one row shows a bracket and
        wire-stub line at all.
        """
        housing = self.housing
        if housing is None:
            return

        terminal = self.db_obj.terminal
        if terminal is None:
            housing.update_terminal_name(self.db_obj.db_id, None, None)
        else:
            housing.update_terminal_name(self.db_obj.db_id, terminal.db_id, terminal.name)

    @staticmethod
    @_check_types.do
    def _build_vbo(name: str) -> "_text.Text":
        """Build this cavity's own name label -- doubles as this
        object's ``_vbo`` (see the class docstring). Called both at
        construction and whenever this cavity's name changes (see
        :meth:`_on_name_changed`) -- ``Text`` has no in-place content-
        update method the way a real VBO's ``.update()`` did, so a
        rename just builds a fresh instance and swaps it in.
        """
        return _text.Text(
            name, Config.object_sizes.cavity.name_font_size,
            build123d.FontStyle.REGULAR)

    @_check_types.do
    def _sync_vbo_transform(self):
        """Push this cavity's own current position/angle into its
        ``Text`` vbo's own transform.

        ``self._position`` (see ``objects_schematic/housing.py``'s
        ``Housing._layout_children``) is this cavity's own slot's
        top-left corner, exactly on the housing's own pin edge -- the
        actual rendered text sits outside and below that anchor:

        - X: shifted left (outside the housing) by the shared
          ``Config.object_sizes.pin_edge_padding`` gap, then further
          left by the label's own measured width -- ``Text``'s local
          x=0 is its own LEFT edge, so this is what makes the label
          read RIGHT-aligned, ending exactly ``pin_edge_padding``
          outside the pin edge (the same shared value the terminal's
          own "(" bracket also offsets by, and the reason the two land
          at the same X -- not because one is aligned to the other).
        - Z: shifted by ``shapes.text.CHARACTER_HEIGHT`` (the tallest
          glyph in the font, at font_size=1.0 -- scaled to this
          cavity's own font size) to reach the label's own baseline --
          a ``Text``'s local y=0 already IS the glyph baseline, so this
          is the only Z offset needed to drop from the slot's top edge
          down to where the glyphs actually sit.

        ``Text`` has no reactive binding of its own to
        ``self._position``/``self._angle`` the way a bound
        ``Point``/``Angle`` does, so this must be called explicitly any
        time either changes -- construction, :meth:`_update_position`,
        :meth:`_update_angle`, :meth:`_rebuild`.
        """
        if self._vbo is None:
            return

        # Bottom-right corner of _local_text_corners() -- the label's
        # own RIGHT/BOTTOM anchor point, in local space.
        local_offset = _point.Point(*self._local_text_corners()[3].tolist())
        offset = local_offset @ self._angle
        self._vbo.set_transform(self._position + offset, self._angle)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        super()._update_position(position)
        self._sync_vbo_transform()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        super()._update_angle(angle)
        self._sync_vbo_transform()

    @_check_types.do
    def _local_text_corners(self) -> np.ndarray:
        """This cavity's own rendered text bounds, as 4 corners in
        housing-local space relative to :attr:`_position` (not yet
        rotated/translated) -- the same right edge/baseline anchor
        :meth:`_sync_vbo_transform` places the label at, expanded by
        its own measured width/height. Shared by :meth:`_compute_obb`/
        :meth:`_compute_aabb`, since a Text's own ``local_obb``/
        ``local_aabb`` (see its VBOHandlerBase-compatible interface)
        are harmless no-op placeholders, not real geometry.
        """
        w = self._vbo.width
        h = self._vbo.height
        font_size = Config.object_sizes.cavity.name_font_size

        right_x = -Config.object_sizes.pin_edge_padding
        left_x = right_x - w
        baseline_z = _text.CHARACTER_HEIGHT * font_size
        top_z = baseline_z - h

        return np.array([
            [left_x, 0.0, top_z], [left_x, 0.0, baseline_z],
            [right_x, 0.0, top_z], [right_x, 0.0, baseline_z],
        ], dtype=np.float32)

    @_check_types.do
    def _compute_obb(self):
        """Derive this object's OBB from :meth:`_local_text_corners`."""
        if self._vbo is None:
            return

        local = self._local_text_corners()
        local @= self._angle
        self._obb = local + self._position

    @_check_types.do
    def _compute_aabb(self):
        """Same corners as :meth:`_compute_obb` -- see its docstring."""
        if self._vbo is None:
            return

        corners = self._local_text_corners()
        corners @= self._angle
        corners += self._position.as_numpy

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Rebuild this cavity's name label from its current name and
        re-derive its OBB/AABB. Bound to fire whenever this cavity's
        own name changes.
        """
        with self.editor2d.editor.context:
            self._vbo = self._build_vbo(self.db_obj.name)
            self._compute_obb()
            self._compute_aabb()
            self._sync_vbo_transform()

        self.editor2d.Refresh()

    @_check_types.do
    def _delete(self):
        self._name_cb.unbind()
        self._terminal_cb.unbind()
        super()._delete()
