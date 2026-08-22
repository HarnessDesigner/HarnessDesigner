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
from ...shapes import text as _text
from . import chain_edges as _chain_edges

from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ...ui import editor_pegboard as _editor_pegboard
    from ...database import project_db as _project_db
    from ...database.global_db import model3d as _model3d


Config = _config.Config.editor_pegboard


class BasePegboard(_objectsvar.BaseVar):
    """
    Base class for Peg Board Editor representations of objects.

    Every :class:`~harness_designer.objects.object_base.ObjectBase`
    subclass gets its own dedicated peg-board wrapper class (this one, or a
    subclass of it) -- never a single shared generic placeholder used
    across unrelated types, even for object types that have no rendering
    presence on the board. A dedicated concrete class per type keeps type
    hints precise (and lets Cython type each attribute exactly) the same
    way ``objschematic``/``obj3d`` already do.

    Mirrors ``objects.objects_3d.base_3d.Base3D``'s API and internals as
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
    read straight from ``db_obj.position_pegboard``/``db_obj.angle_pegboard``
    (see ``database.project_db.mixins.position_pegboard.
    PositionPegboardMixin``/``mixins.angle_pegboard.AnglePegboardMixin``,
    which mirror ``position3d``/``angle3d`` exactly: a shared
    ``pjt_points_pegboard`` table + FK column, and
    redundant quat/Euler TEXT columns, respectively). Every mutation writes
    to the database immediately via the mixin's own bound callback -- same
    "no batching, no deferred commit" discipline ``position3d``/``angle3d``
    already use for live 3D dragging.
    """

    @_check_types.do
    def __init__(
        self,
        parent: "_ObjectBase",
        db_obj: "_project_db.PJTEntryBase",
        vbo: _vbo.VBOHandlerBase | _text.Text | None = None,
        angle: _angle.Angle | None = None,
        position: _point.Point | None = None,
        scale: _point.Point | None = None,
        material: _materials.GLMaterial | None = None
    ):
        """
        Initialise the :class:`BasePegboard` instance.

        :param parent: Parent object.
        :type parent: _ObjectBase
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        :param vbo: The mesh VBO to render with -- a placeholder box/
            cylinder (matching the housing/splice/terminal subclasses'
            own ``objects.objects_3d`` counterparts' placeholder-shape
            choice) until an anchor type's model finishes its (possibly
            async) load and :meth:`_set_model` swaps in the real one.
            ``None`` only for object types with no peg-board rendering
            presence at all (every do-nothing ``objects_pegboard`` stub, and a
            seated :class:`~harness_designer.objects.objects_pegboard.terminal.Terminal`)
            -- passing ``None`` here also leaves ``position``/``angle``/
            ``scale``/``material`` entirely unset, regardless of what's
            passed for them, so real anchor types must never do this.
        :type vbo: :class:`_vbo.VBOHandlerBase` | None
        :param angle: Live, bindable peg-board rotation (``db_obj.angle_pegboard``).
        :type angle: :class:`_angle.Angle` | None
        :param position: Live, bindable peg-board position (``db_obj.position_pegboard``).
        :type position: :class:`_point.Point` | None
        :param scale: A freshly-built scale, never borrowed from ``obj3d``
            (another view's own live, mutable instance) -- either read
            straight from the database (``db_obj.scale3d``, when that
            mixin is present) or computed fresh from the catalog part's
            own dimensions, matching how ``objects_3d`` builds its own.
        :type scale: :class:`_point.Point` | None
        :param material: A freshly-built material, never borrowed from
            ``obj3d`` -- rebuilt from the catalog part's own color, same
            construction ``objects_3d`` uses for its own material.
        :type material: :class:`_materials.GLMaterial` | None
        """

        self.pegboard: "_editor_pegboard.EditorPegboard" = parent.mainframe.editor_pegboard

        # Identity key for gl.canvas_pegboard's bundle-graph matching and
        # this anchor's own data-table(s) -- set by each real subclass's
        # __init__ (housing/splice/transition/terminal); left None for
        # every do-nothing objects_pegboard stub, and for a seated Terminal.
        self.point3d_id: int | None = None

        super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        try:
            self._is_visible = self.db_obj.is_visible_pegboard  # NOQA
            self.db_obj.bind(self.__is_visible_callback, 'is_visible_pegboard')
        except AttributeError:
            self._is_visible = False

    @_check_types.do
    def drag(self, delta: _point.Point) -> None:
        """Same as :meth:`BaseVar.drag`, but locked to the X/Z board
        plane -- this view's camera is permanently locked top-down
        looking straight down world Y, so Y movement is never meaningful
        here regardless of object type.
        """
        super().drag(_point.Point(delta.x, 0.0, delta.z))

    @_check_types.do
    def touching_budgets(self) -> list:
        """Return the length budget(s) for every wire/bundle segment
        directly attached to this anchor's own peg-board point.

        Default implementation for a real anchor (housing/terminal/
        transition -- anything with a real, DB-backed :attr:`point3d_id`
        that's a genuine start/stop endpoint for wires/bundles, not a
        waypoint along one -- ``wire_layout.WireLayout``/
        ``bundle_layout.BundleLayout`` override this instead with their
        own interior-waypoint version, see their own docstrings).

        Scans every wire and bundle in the project for one whose start or
        stop point matches this anchor's own :attr:`point3d_id` -- there
        is no reverse index from a point to the wires/bundles that
        reference it. Cheap enough to only ever call once per drag-arm
        (never per mouse-move) -- same cost/call-frequency discipline the
        pre-migration graph-based version used.
        """
        if self.point3d_id is None:
            return []

        from . import chain_edges as _chain_edges

        project = self.parent.mainframe.project
        budgets = []

        for wire in project.ptables.pjt_wires_table:
            budgets.extend(_chain_edges.touching_edges(wire, self.point3d_id))

        for bundle in project.ptables.pjt_bundles_table:
            budgets.extend(_chain_edges.touching_edges(bundle, self.point3d_id))

        return budgets

    @property
    @_check_types.do
    def editor(self):
        return self.pegboard

    @_check_types.do
    def __is_visible_callback(self, *_, **__):
        self._is_visible = self.db_obj.is_visible_pegboard  # NOQA

    @property
    @_check_types.do
    def is_visible(self) -> bool:
        """
        Get object visibility

        :rtype: bool
        """

        return self._is_visible

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool):
        """
        Set object visibility.

        :type value: bool
        """
        self._is_visible = value

        try:
            self.db_obj.is_visible_pegboard = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def _selected_color(self) -> _color.Color:
        return _color.Color(*Config.selected_color)

    @_debug.logfunc
    @_check_types.do
    def _set_model(self, model: "_model3d.Model3D"):
        """Async model-load callback -- mirrors
        ``objects.objects_3d.base_3d.Base3D._set_model`` exactly (same
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
        with self.pegboard.context:
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

        # Already registered from construction time (is_active was already
        # True with the placeholder vbo) -- add_object()/add_anchor() is
        # idempotent, so this is only ever a real registration for the
        # rare case _set_model fires before mainframe.add_object() ever
        # ran (e.g. a synchronous, already-cached model.load() call during
        # __init__ itself).
        self.pegboard.add_object(self.parent)
        self.pegboard.Refresh()

    @property
    @_check_types.do
    def obj(self) -> "_ObjectBase":
        """Return the owning :class:`ObjectBase` wrapper (back-reference).

        Same object as :attr:`parent` -- named ``obj`` to match the
        rendering/hit-testing code in ``gl.canvas_pegboard`` (e.g.
        ``anchor.obj.is_selected``).

        :returns: Property value.
        :rtype: _ObjectBase
        """
        return self.parent

    @_check_types.do
    def delete(self):
        self.parent.delete()

    @_check_types.do
    def _delete(self):
        self._is_deleted = True
        self.pegboard.Refresh()
