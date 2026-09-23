# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import build123d
import numpy as np

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import cavity_layout as _cavity_layout
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


def _is_180(degrees: float) -> bool:
    """Whether *degrees* (the owning housing's own live ``angle.y``) is
    the 180 special case -- rotating this cavity's own name glyph a
    full half-turn along with the housing would render it upside-down,
    so at that one angle the glyph itself renders upright instead (see
    :meth:`Cavity.render`).
    """
    return round(degrees) % 360 == 180


# What a label is drawn with at exactly 180 degrees -- see Cavity.render.
_NO_ROTATION = _angle.Angle()


class Cavity(_base_schematic.BaseSchematic):
    """
    2D representation of a cavity for schematic view

    Renders only this cavity's own name -- RIGHT/BOTTOM-aligned text
    sitting just outside its owning housing's rectangle, a fixed gap
    above its terminal's own bracket. Its ``Text`` label (see
    ``shapes/text.py``) IS this object's own ``_vbo`` -- ``Text``
    implements the same public interface a real VBO handler does (see
    its own "VBOHandlerBase-compatible interface" section), so the
    standard inherited ``BaseVar`` pipeline draws it, matching how
    ``Base3D`` subclasses render -- :meth:`render` only swaps in the
    housing's angle around it (see :meth:`_render_label`).
    ``_compute_obb``/``_compute_aabb`` are overridden: the click target is
    the label's own box (``Text.local_obb``/``local_aabb``) turned by the
    angle the label is drawn with and moved to its position, and nothing
    can be worked out until the owning housing is known (see :attr:`housing`
    and :meth:`render`).

    ``position2d``/``angle2d`` are written once, batched, by
    ``database/project_db/pjt_housing.py``'s ``PJTHousingsTable.insert``
    at housing-insert time -- but that position is this cavity's own
    slot's CENTER (both axes -- see ``geometry.cavity_layout.
    cavity_slot_position``), not the label's own RIGHT/BOTTOM anchor
    point (see :meth:`_rebuild_geometry`/:attr:`_geometry`). Unlike
    ``objects_schematic/cavity.py``'s older design, this cavity's own
    render position is no longer derived by offsetting from
    ``self._position`` directly -- it's derived fresh from the owning
    housing's own LIVE position/angle (see :meth:`_local_to_world`), the
    same way ``objects_schematic/terminal.py``'s ``Terminal`` already
    works, so a housing ROTATION (not just a move) repositions this
    cavity's own label correctly too.

    Owns two DB binds on itself: its own ``'name'`` (rebuilds this
    cavity's own text mesh -- see :meth:`_on_name_changed`) and the
    synthetic ``'terminal_id'`` tag (currently a no-op here -- see
    :meth:`_on_terminal_changed`). ``objects_schematic/housing.py``'s
    ``Housing`` no longer binds to either tag itself, or does any
    relayout of its own children at all (that was removed
    2026-09-10, Kevin -- see that class's own docstring) -- repositioning
    a seated terminal after a name/terminal change is this cavity's own
    responsibility now, if/when :meth:`_rebuild`/:meth:`_on_terminal_changed`
    actually do it (both are currently no-ops -- see their own docstrings).
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    # Narrower than BaseVar's own generic `_vbo.VBOHandlerBase | None`
    # -- this object's only visible content is the Text label it owns
    # (see _build_vbo), never a real mesh VBO.
    _vbo: _text.Text = None

    # Cached housing-local geometry (name label anchor + hit-test box)
    # -- see :meth:`_rebuild_geometry`.
    _geometry: _cavity_layout.CavityGeometry = None

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

        # this position is not the center of the cavity but is instead the
        # center of the cavity text.
        position = db_obj.position2d

        # this is the angle of the cavity text
        angle = db_obj.angle2d

        # this is the scale of the cavity text
        scale = _point.Point(1.0, 1.0, 1.0)

        material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            self._geometry = db_obj.housing.cavity_geometry.get(db_obj.db_id)

            vbo = self._geometry.text

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

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
        housing = self.db_obj.housing

        housing_obj = housing.get_object()
        if housing_obj is None:
            return None

        return housing_obj.objschematic

    @_check_types.do
    def _on_name_changed(self, _entry=None):
        """Rebuild this cavity's own name mesh (see :meth:`_rebuild`).
        ``objects_schematic/housing.py``'s ``Housing`` no longer binds
        to this tag or does any relayout of its own -- see this class's
        own docstring.
        """
        self._rebuild()

    @_check_types.do
    def _on_terminal_changed(self, _entry=None):
        """No-op -- see this class's own docstring: repositioning a
        seated terminal after this fires is not currently handled
        anywhere (``objects_schematic/housing.py``'s ``Housing`` used to
        do it as part of a full relayout, but that was removed
        2026-09-10, Kevin, and nothing has replaced it yet).
        """
        pass

    @_check_types.do
    def _local_to_world(self, local_x: float, local_z: float) -> _point.Point:
        """Rotate+translate a housing-local ``(local_x, 0, local_z)``
        point by the owning housing's own LIVE position/angle -- same
        as ``objects_schematic/terminal.py``'s ``Terminal.
        _local_to_world`` (see its own docstring).
        """
        housing = self.housing

        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        wx, wy, wz = _base_schematic._rotate_about_y(points, housing.angle.y)[0]  # NOQA

        return _point.Point(
            housing.position.x + float(wx),
            housing.position.y + float(wy),
            housing.position.z + float(wz))

    @_check_types.do
    def _rebuild_geometry(self):
        """Fetch this cavity's own precomputed schematic geometry
        straight from ``PJTHousing.cavity_geometry`` (see that
        property's own docstring for why this is precomputed there
        rather than derived here) and refresh the WORLD obb/aabb from
        it.

        Cheap (a dict lookup) and always succeeds regardless of this
        object's own construction state -- unlike the SCHEMATIC
        :attr:`housing` (needed only for the live position/angle
        transform in :meth:`_compute_obb`/:meth:`_compute_aabb`/
        :meth:`render`, and genuinely unresolvable at this cavity's own
        construction time -- see that property's own docstring),
        ``self.db_obj.housing`` (the DB-layer ``PJTHousing``) has no
        such dependency at all.
        """
        self._geometry = self.db_obj.housing.cavity_geometry.get(self.db_obj.db_id)

        self._compute_obb()
        self._compute_aabb()

    @property
    @_check_types.do
    def obb(self) -> np.ndarray:
        """The generic box until the housing is known, then the one worked
        out from the label (see :meth:`_compute_obb`)."""
        if self.housing is None:
            return super().obb

        if self._obb is None:
            self._compute_obb()
            self._compute_aabb()

        return self._obb

    @property
    @_check_types.do
    def aabb(self) -> np.ndarray:
        """See :attr:`obb`."""
        if self.housing is None:
            return super().aabb

        if self._obb is None:
            self._compute_obb()
            self._compute_aabb()

        return self._aabb

    def _label_angle(self, housing) -> _angle.Angle:
        """The angle this cavity's name is drawn at -- the same one
        :meth:`render` uses: the housing's, except at exactly 180 degrees where
        the glyph is drawn upright instead."""
        if _is_180(housing.angle.y):
            return _NO_ROTATION

        return housing.angle

    @_check_types.do
    def _compute_obb(self):
        """The label's own OBB (``Text.local_obb``) turned and moved to where
        the label is drawn. Nothing to do until the housing is known."""
        housing = self.housing
        if housing is None or self._vbo is None or self._position is None:
            return

        obb = self._vbo.local_obb.copy()
        obb @= self._label_angle(housing)
        obb += self._position.as_numpy

        # the first time there is no array yet: it comes from the pool
        if self._obb is None:
            self._obb = self._obb_manager.read(self._obb_index)

        self._obb[:] = obb

    @_check_types.do
    def _compute_aabb(self):
        """The label's own AABB (``Text.local_aabb``) turned and moved to where
        the label is drawn, then ``utils.adjust_aabb`` so every min is in the
        min row and every max in the max row. Nothing to do until the housing
        is known."""
        housing = self.housing
        if housing is None or self._vbo is None or self._position is None:
            return

        local = self._vbo.local_aabb
        corners = _utils.compute_obb(
            _point.Point(*local[0].tolist()), _point.Point(*local[1].tolist()))

        corners @= self._label_angle(housing)
        corners += self._position.as_numpy

        self._aabb[:] = _utils.adjust_aabb(corners)

    @_check_types.do
    def hit_test_step2(self, ray_origin, ray_direction):
        """Only the box is tested (see :meth:`hit_test_step3`)."""
        return _base_schematic.box_hit_test(self._obb, ray_origin, ray_direction)

    @_check_types.do
    def hit_test_step3(self, ray_origin, ray_dir):
        """A cavity is picked by its name label's box -- the OBB -- not by
        the label's glyph triangles: the pool's own OBB test already said the
        ray is inside it, and nothing finer is wanted."""
        return _base_schematic.box_hit_test(self._obb, ray_origin, ray_dir)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Re-run :meth:`_rebuild_geometry` -- not just
        :meth:`_compute_obb`/:meth:`_compute_aabb` on the already-cached
        :attr:`_geometry` -- for two reasons:

        1. :attr:`housing` is typically unresolvable at this cavity's
           own construction time (see that property's own docstring),
           so :attr:`_geometry` is often still ``None`` the first time
           this fires -- exactly like
           ``objects_schematic/terminal.py``'s ``Terminal`` (whose own
           ``_update_position`` also calls its own
           ``_rebuild_geometry`` for the same reason), this is the
           retroactive rebuild that actually populates it once the
           housing does become resolvable.
        2. Once :attr:`_geometry` IS already populated, re-deriving the
           WORLD obb/aabb from the owning housing's own current
           position/angle is required anyway -- not the inherited
           generic cheap delta-translate (``BaseVar._update_position``'s
           ``self._obb += delta``), which is only valid for a pure
           translation. A housing ROTATION also moves this cavity's own
           ``position2d`` (see ``PJTHousing._update_angle2d``), but by a
           rotate-about-pivot delta, not a uniform translate -- and this
           cavity's own hit box sits at a fixed HOUSING-LOCAL offset
           from its own anchor, which itself needs re-rotating, not
           just shifting, to track that correctly.
        """
        super()._update_position(position)
        self._rebuild_geometry()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """See :meth:`_update_position` -- same reason. Never actually
        fires in practice (this cavity's own ``angle2d`` is never
        touched by anything in this pipeline) but overridden
        defensively, matching ``objects_schematic/terminal.py``'s
        ``Terminal`` doing the same.
        """
        super()._update_angle(angle)
        self._rebuild_geometry()

    @_check_types.do
    def render(self, shaders):
        """The first draw of this cavity: work out its box, then hand every
        later draw straight to :meth:`_render_label`.

        The housing is not known yet when this cavity is built (see
        :attr:`housing`), so its box could not be worked out then, and nothing
        moves a cavity after a project loads -- so it is done the first time it
        is drawn, when the housing does exist. The picker reads the bounds pool
        directly, so the box has to be in it before a click can find this
        cavity.

        Once it is there, ``render`` is replaced on this instance by
        :meth:`_render_label`, so the check is never made again. (If the housing
        is somehow still unknown, this stays in place and tries again next
        frame.)
        """
        self._compute_obb()
        self._compute_aabb()

        if self._obb is not None:
            self.render = self._render_label

        self._render_label(shaders)

    @_check_types.do
    def _render_label(self, shaders):
        """Render this cavity's own name label -- swapping ``self._angle``
        (never this cavity's own, always-identity ``db_obj.angle2d`` --
        see the class docstring) for the owning housing's own CURRENT
        angle before delegating to the inherited pipeline, so the label
        rotates along with its housing at 0/90/270. At 180, a full
        half-turn would render the glyph upside-down, so the angle is
        forced back to identity there instead (see :func:`_is_180`).

        NOTE: this does not also flip the label's own internal h_align
        the way ``objects_schematic/housing.py``'s ``Housing`` does for
        its own (always multi-line) corner label -- h_align only
        affects a MULTI-line block's own internal line-justification
        (see ``shapes/text.py``'s own docstring: "a single-line Text
        always renders identically regardless of this"), and a
        cavity's own name is single-line in the overwhelming common
        case, so there's nothing for it to visibly change. A cavity
        name containing an explicit newline would still read
        unmirrored at 180 -- flag if that's not acceptable, since
        fixing it means rebuilding this cavity's own ``self._geometry.
        text`` with a different h_align, distinct from every other
        cavity sharing the same housing-wide ``PJTHousing.
        cavity_geometry`` cache entry set.
        """
        if not self.is_visible or self._position is None:
            return

        housing = self.housing
        if housing is None:
            return

        real_angle = self._angle

        if _is_180(housing.angle.y):
            self._angle = _angle.Angle()
        else:
            self._angle = housing.angle

        super().render(shaders)

        self._angle = real_angle

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Rebuild this cavity's name label from its current name and
        re-derive its own geometry/OBB/AABB. Bound to fire whenever
        this cavity's own name changes.
        """
        # with self.editor2d.editor.context:
        #     self._vbo = self._build_vbo(self.db_obj.name)
        #     self._rebuild_geometry()

        self.editor2d.Refresh()

    @_check_types.do
    def _delete(self):
        self._name_cb.unbind()
        self._terminal_cb.unbind()
        super()._delete()
