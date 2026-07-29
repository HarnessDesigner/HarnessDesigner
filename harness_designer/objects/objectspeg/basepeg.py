# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color
from ... import config as _config
from ...gl import materials as _materials
from .. import objectsvar as _objectsvar
from ...gl import vbo as _vbo

from ... import debug as _debug


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ...ui import editor_pegboard as _editor_pegboard
    from ...database import project_db as _project_db
    from ...database.global_db import model3d as _model3d


Config = _config.Config.editor_pegboard

# A freshly-created ``anglepeg``/``quatpeg`` row always starts at this exact
# identity quaternion (see database.create_database.housings/splices/
# transitions/terminals' column defaults) -- used as the "has the user (or a
# prior flatten pass) ever actually set this anchor's rotation" sentinel by
# :meth:`BasePeg._apply_flatten_if_untouched`. A user who deliberately spins
# an anchor back to exactly this orientation is an accepted, harmless edge
# case (re-applying the flatten default would be a no-op-equivalent visually
# in that exact case, not a correctness bug).
_IDENTITY_QUAT = (1.0, 0.0, 0.0, 0.0)
_IDENTITY_TOLERANCE = 1e-6


class BasePeg(_objectsvar.BaseVar):
    """
    Base class for Peg Board Editor representations of objects.

    Every :class:`~harness_designer.objects.object_base.ObjectBase`
    subclass gets its own dedicated peg-board wrapper class (this one, or a
    subclass of it) -- never a single shared generic placeholder used
    across unrelated types, even for object types that have no rendering
    presence on the board. A dedicated concrete class per type keeps type
    hints precise (and lets Cython type each attribute exactly) the same
    way ``obj2d``/``obj3d`` already do.

    Mirrors ``objects.objects3d.base3d.Base3D``'s API and internals as
    closely as possible (same ``position``/``angle``/``scale``/``material``/
    ``vbo`` surface, same ``_update_position``/``_update_angle``/
    ``_update_scale``/``_compute_obb``/``_compute_aabb``/``set_selected``
    shape, same ``_set_model`` async-model-load hook) -- there is
    deliberately no separate "richer" subclass for the 4 anchor types that
    render (housing, splice, transition, bare terminal): this class handles
    both the "real anchor" case (``vbo``/``angle``/``position``/``scale``/
    ``material`` all provided) and the "no rendering presence" case (all of
    those left ``None``) via one constructor. Most object types (notes,
    cavities, covers, seals, locks, wire sub-features, etc.) construct this
    base directly with everything left at its ``None`` default and add
    nothing else.

    Position/rotation are real, independent, DB-backed values -- not split
    apart into separate x/z floats or a separately-recombined quaternion --
    read straight from ``db_obj.position_peg``/``db_obj.anglepeg`` (see
    ``database.project_db.mixins.position_peg.PositionPegMixin``/
    ``mixins.angle_peg.AnglePegMixin``, which mirror ``position2d``/
    ``angle2d`` exactly: a shared ``pjt_points_peg`` table + FK column, and
    redundant quat/Euler TEXT columns, respectively). Every mutation writes
    to the database immediately via the mixin's own bound callback -- same
    "no batching, no deferred commit" discipline ``position3d``/``angle3d``
    already use for live 3D dragging.
    """

    def __init__(
        self,
        parent: "_ObjectBase",
        db_obj: "_project_db.PJTEntryBase",
        vbo: "_vbo.VBOHandlerBase" = None,
        angle: _angle.Angle = None,
        position: _point.Point = None,
        scale: _point.Point = None,
        material: _materials.GLMaterial = None
    ):
        """
        Initialise the :class:`BasePeg` instance.

        :param parent: Parent object.
        :type parent: _ObjectBase
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        :param vbo: The mesh VBO to render with -- a placeholder box/
            cylinder (matching the housing/splice/terminal subclasses'
            own ``objects.objects3d`` counterparts' placeholder-shape
            choice) until an anchor type's model finishes its (possibly
            async) load and :meth:`_set_model` swaps in the real one.
            ``None`` only for object types with no peg-board rendering
            presence at all (every do-nothing ``objectspeg`` stub, and a
            seated :class:`~harness_designer.objects.objectspeg.terminal.Terminal`)
            -- passing ``None`` here also leaves ``position``/``angle``/
            ``scale``/``material`` entirely unset, regardless of what's
            passed for them, so real anchor types must never do this.
        :type vbo: :class:`_vbo.VBOHandlerBase` | None
        :param angle: Live, bindable peg-board rotation (``db_obj.anglepeg``).
        :type angle: :class:`_angle.Angle` | None
        :param position: Live, bindable peg-board position (``db_obj.position_peg``).
        :type position: :class:`_point.Point` | None
        :param scale: The real 3D scale to reuse.
        :type scale: :class:`_point.Point` | None
        :param material: The real 3D material to reuse.
        :type material: :class:`_materials.GLMaterial` | None
        """

        self.pegboard: "_editor_pegboard.EditorPegBoard" = parent.mainframe.editor_pegboard

        # Identity key for gl.canvas_pegboard's bundle-graph matching and
        # this anchor's own data-table(s) -- set by each real subclass's
        # __init__ (housing/splice/transition/terminal); left None for
        # every do-nothing objectspeg stub, and for a seated Terminal.
        self.point3d_id: int | None = None

        super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    @property
    def editor(self):
        return self.pegboard

    def _is_visible_callback(self, *_, **__):
        pass

    @property
    def is_visible(self) -> bool:
        """
        Get object visibility

        :rtype: bool
        """

        return True

    @is_visible.setter
    def is_visible(self, value: bool):
        """
        Set object visibility.

        :type value: bool
        """

        pass

    @property
    def _selected_color(self) -> _color.Color:
        return _color.Color(*Config.selected_color)

    def _apply_flatten_if_untouched(self, euler: tuple) -> None:
        """Apply a computed "lay it flat" Euler orientation to
        :attr:`angle`, but only if the anchor's rotation is still at the
        fresh-row identity default -- never clobbers a real user rotation
        (or a previously-applied flatten).

        Setting ``.x``/``.y``/``.z`` one at a time (there is no bulk
        "replace this Angle's rotation in place" API -- see
        ``geometry.angle.Angle``) fires the bound DB-write callback on
        each assignment, exactly like every other live peg-board rotation
        edit -- three quick synchronous writes for a one-time
        initialization event is no different from what a rotate-drag
        already does per mouse-move.

        :param euler: ``(x, y, z)`` Euler degrees to apply.
        :type euler: tuple[float, float, float]
        """
        if self._angle is None:
            return

        current_quat = tuple(float(v) for v in self._angle.as_quat_float)
        if not all(abs(a - b) < _IDENTITY_TOLERANCE
                   for a, b in zip(current_quat, _IDENTITY_QUAT)):
            return

        ex, ey, ez = euler
        self._angle.x = ex
        self._angle.y = ey
        self._angle.z = ez

    @_debug.logfunc
    def _set_model(self, model: "_model3d.Model3D"):
        """Async model-load callback -- mirrors
        ``objects.objects3d.base3d.Base3D._set_model`` exactly (same
        ``PooledVBOHandler``-by-UUID reuse), registered via
        ``model.load(manufacturer, part_number, self._set_model)`` by the
        real anchor subclasses (housing/splice/terminal -- transitions have
        no catalog ``Model3D``, so never call this). Fires synchronously if
        the model is already cached, asynchronously otherwise -- either way,
        this is what swaps this anchor's placeholder box/cylinder ``vbo``
        (already real, already ``is_active``, set at construction time --
        see :meth:`__init__`) for the real catalog mesh.

        :param model: The now-loaded model.
        :type model: :class:`_model3d.Model3D`
        """
        self.pegboard.context.acquire()

        uuid = model.uuid

        if uuid in _vbo.PooledVBOHandler:
            vbo = _vbo.PooledVBOHandler(uuid)
        else:
            vbo = _vbo.create_model_vbo(model)

        vbo.acquire()

        self._vbo = vbo

        # Mirrors Base3D._set_model exactly: once the real mesh is in,
        # swap the placeholder-derived scale (width/height/length, or
        # diameter/length -- whatever the real subclass's __init__ built
        # it from) for the row's own live, DB-backed scale3d, if it has
        # one (Housing/Splice/Terminal all do, via Scale3DMixin). Without
        # this, the peg board would keep rendering at the placeholder's
        # frozen scale forever, never picking up scale3d or its live edits.
        try:
            scale = self.db_obj.scale3d  # NOQA
            self._scale.unbind(self._update_scale)
            self._scale = scale
            self._o_scale = self._scale.copy()
            self._scale.bind(self._update_scale)
        except AttributeError:
            pass

        self._compute_obb()
        self._compute_aabb()

        self.pegboard.context.release()

        flatten_hook = getattr(self, '_flatten_hook', None)
        if flatten_hook is not None:
            self._apply_flatten_if_untouched(flatten_hook())

        self.pegboard.Refresh()

        # Already registered from construction time (is_active was already
        # True with the placeholder vbo) -- add_object()/add_anchor() is
        # idempotent, so this is only ever a real registration for the
        # rare case _set_model fires before mainframe.add_object() ever
        # ran (e.g. a synchronous, already-cached model.load() call during
        # __init__ itself).
        self.pegboard.add_object(self.parent)

    @property
    def obj(self) -> "_ObjectBase":
        """Return the owning :class:`ObjectBase` wrapper (back-reference).

        Same object as :attr:`parent` -- named ``obj`` to match the
        rendering/hit-testing code in ``gl.canvas_pegboard`` (e.g.
        ``anchor.obj.is_selected``).

        :returns: Property value.
        :rtype: _ObjectBase
        """
        return self.parent

    @property
    def is_active(self) -> bool:
        """Return whether this anchor has a real, rendered peg-board
        presence right now.

        ``True`` once a real ``vbo`` exists (either provided at
        construction, e.g. ``Transition``, or set later by
        :meth:`_set_model` once an async model load finishes) --
        ``False`` for every do-nothing object type, and for a
        ``Terminal`` currently seated in a cavity.

        :returns: Property value.
        :rtype: bool
        """
        return self._vbo is not None

    def delete(self):
        self.parent.delete()

    def _delete(self):
        self._is_deleted = True
        self.pegboard.Refresh()

    @property
    def smooth(self) -> bool:
        """Return whether the mesh renders with smooth (vertex) normals.

        :returns: Property value.
        :rtype: bool
        """
        return getattr(self, '_smooth', False)

    @smooth.setter
    def smooth(self, value: bool) -> None:
        self._smooth = bool(value)

    # ------------------------------------------------------------------
    # Peg Board Editor data-table overlays (gl.canvas_pegboard.tables_overlay)
    # ------------------------------------------------------------------

    def _table_label(self) -> str:
        """Title-strip text for this anchor's own (single) data table.

        :returns: This anchor's DB name, or its class name if unset.
        :rtype: str
        """
        name = getattr(self.db_obj, 'name', '')
        return name or type(self.obj).__name__

    @property
    def table_anchor_points(self) -> list:
        """Every ``(point3d_id, world_x, world_z, label)`` this anchor
        needs its own data table for.

        Every ordinary anchor has exactly one -- its own ``point3d_id``/
        live ``position`` -- so the base implementation covers housing/
        splice/bare-terminal directly.
        :class:`~harness_designer.objects.objectspeg.transition.Transition`
        overrides this to return one entry per populated branch (1-6),
        since each branch needs an independent table (a branch's own
        ``position3d_id`` is a distinct point from the transition's own
        anchor point). Inactive anchors (``is_active`` ``False``, or the
        do-nothing stub classes for object types with no board presence)
        return an empty list -- nothing to show a table for.

        :returns: This anchor's table-anchor points.
        :rtype: list[tuple[int, float, float, str]]
        """
        if not self.is_active or self.point3d_id is None:
            return []

        return [(self.point3d_id, float(self.position.x), float(self.position.z),
                 self._table_label())]

    def table_anchor_live_position(self, point3d_id: int) -> _point.Point:
        """Return the live, bound ``Point`` backing *point3d_id* -- one of
        this anchor's own :attr:`table_anchor_points` ids.

        Unlike the plain floats :attr:`table_anchor_points` returns (a
        one-time snapshot), this is the very same ``Point`` object this
        anchor's own position mutates in place on every drag (see
        :meth:`_update_position`/``PositionPegMixin``). Callers that need
        to keep tracking a moving anchor after the snapshot was taken --
        the table-drag leader line,
        ``gl.canvas_pegboard.tables_overlay.PegboardTableWidget`` -- must
        hold onto *this* reference instead of copying x/z out of it into
        a new, disconnected ``Point``, or the line's anchor-side endpoint
        goes stale the moment the anchor is moved and committed without a
        table-overlay rebuild in between.

        Every ordinary anchor has exactly one point3d_id (its own), so the
        base implementation just returns :attr:`position` directly.
        :class:`~harness_designer.objects.objectspeg.transition.Transition`
        overrides this to resolve *point3d_id* to the matching branch's
        own live ``position3d`` instead.

        :param point3d_id: One of this anchor's own :attr:`table_anchor_points` ids.
        :type point3d_id: int
        :returns: The live position ``Point``.
        :rtype: :class:`_point.Point`
        """
        return self.position

    def build_table_rows(self, project, point3d_id: int) -> list:
        """Return this anchor's wire rows for the table anchored at
        *point3d_id* -- one of the id(s) :attr:`table_anchor_points`
        returned.

        Overridden per concrete anchor subclass (housing/splice/
        transition/bare-terminal); the base implementation returns an
        empty list, covering every do-nothing ``objectspeg`` stub class
        for object types that never appear on the board.

        :param project: The currently open project.
        :type project: :class:`harness_designer.objects.project.Project`
        :param point3d_id: One of this anchor's own :attr:`table_anchor_points` ids.
        :type point3d_id: int
        :returns: This table's rows.
        :rtype: list[:class:`~harness_designer.gl.canvas_pegboard.table_rows.WireTableRow`]
        """
        return []

    @property
    def table_include_cavity_columns(self) -> bool:
        """Whether this anchor's table(s) should include the Cavity
        Index/Cavity Name columns -- ``True`` only for
        :class:`~harness_designer.objects.objectspeg.housing.Housing`.

        :returns: Property value.
        :rtype: bool
        """
        return False
