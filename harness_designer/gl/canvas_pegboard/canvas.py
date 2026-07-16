# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg Board Editor Canvas using OpenGL

Phase 1 skeleton: camera/pan/zoom/grid plumbing only, mirroring
gl.canvas2d.canvas.Canvas exactly where its pattern is canvas-agnostic
(GLContext usage, Camera2D-based orthographic projection, background
clear, ref-counted Refresh()). No peg-board scene-object rendering,
VBO/model reuse, or DB queries happen here -- that is a later task's job,
built on top of the extension points marked below.

wx.glcanvas.GLCanvas -> QOpenGLWidget

  - initializeGL()  one-time GL setup, called once the context is current
  - resizeGL(w, h)  replaces EVT_SIZE handler
  - paintGL()       replaces EVT_PAINT / _on_paint
  - SwapBuffers()   implicit -- Qt does it automatically
  - makeCurrent()   called by GLContext.acquire() (no explicit SetCurrent)
  - GetClientSize() -> self.width(), self.height()
"""

import math
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QSize, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL import GL

from .. import context as _context
from .. import shaders as _shaders
from .. import vbo as _vbo
from .. import materials as _materials
from ... import config as _config
from ... import color as _color
from ...geometry import point as _point
from ..canvas2d import grid as _grid
from . import tables_overlay as _tables_overlay


# Table-overlay drag leader-line -- world-unit (mm) width and RGB color,
# matching PegboardRotationRing's own flat, medium-blue gizmo color so
# every ad hoc (non-real-mesh) peg-board overlay reads as "the same kind
# of UI chrome".
_TABLE_DRAG_LINE_WIDTH_MM = 1.5
_TABLE_DRAG_LINE_COLOR_RGB = (90, 160, 230)


if TYPE_CHECKING:
    from . import layout_graph as _layout_graph
    from . import rotation_ring as _rotation_ring
    from ...objects.objectspeg import basepeg as _basepeg


MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS


class Canvas(QOpenGLWidget):
    """
    Peg Board OpenGL Canvas.

    Provides the same orthographic top-down view as the 2D schematic
    canvas:
    - 1:1 mm mapping (same distance/1000.0 world-per-pixel convention as
      Camera2D)
    - Pan and zoom, via mouse (MouseHandlerPegBoard) and keyboard
      (KeyHandler)
    - Background reference grid (reuses gl.canvas2d.grid.Grid unchanged --
      it is canvas-agnostic: it only ever touches ``canvas.config``,
      ``canvas.context`` and ``canvas.Refresh()``)

    No scene-object selection/dragging/rendering exists yet -- see the
    "TODO" markers in this file and in mouse_handler.py for where a later
    task hooks that in.
    """

    # GL signals -- same set as canvas2d/canvas3d (mouse/key handlers emit
    # these). Declared now, even though nothing emits the gl_object_* ones
    # yet, so a later task wiring the dock doesn't also need to add them.
    gl_object_selected = Signal(object)
    gl_object_unselected = Signal(object)
    gl_object_activated = Signal(object)
    gl_object_right_click = Signal(object)
    gl_object_right_dclick = Signal(object)
    gl_object_middle_click = Signal(object)
    gl_object_middle_dclick = Signal(object)
    gl_object_aux1_click = Signal(object)
    gl_object_aux1_dclick = Signal(object)
    gl_object_aux2_click = Signal(object)
    gl_object_aux2_dclick = Signal(object)
    gl_object_drag = Signal(object)
    gl_key_down = Signal(object)
    gl_key_up = Signal(object)
    gl_mouse_move = Signal(object)
    gl_left_down = Signal(object)
    gl_left_up = Signal(object)
    gl_left_dclick = Signal(object)
    gl_right_down = Signal(object)
    gl_right_up = Signal(object)
    gl_right_dclick = Signal(object)
    gl_middle_down = Signal(object)
    gl_middle_up = Signal(object)
    gl_middle_dclick = Signal(object)
    gl_aux1_down = Signal(object)
    gl_aux1_up = Signal(object)
    gl_aux1_dclick = Signal(object)
    gl_aux2_down = Signal(object)
    gl_aux2_up = Signal(object)
    gl_aux2_dclick = Signal(object)
    gl_capture_lost = Signal(object)

    def __init__(self, parent, config: "_config.Config.editor_pegboard" = None,
                 size: QSize = None):
        """Initialise the :class:`Canvas` instance.

        :param parent: Parent widget.
        :type parent: UNKNOWN
        :param config: Peg board editor config section. Defaults to
            ``Config.editor_pegboard`` so the canvas is directly usable
            standalone (no host dock exists yet).
        :type config: :class:`_config.Config.editor_pegboard`
        :param size: Optional initial size.
        :type size: :class:`QSize`
        """
        super().__init__(parent)

        # Walk up to mainframe -- same convention as canvas2d.canvas.Canvas.
        # `mainframe.editor_pegboard` doesn't exist yet (the dock is a
        # separate, later task); until it does this gracefully falls back
        # to `parent`, exactly like canvas2d does today.
        w = parent

        while w is not None and not hasattr(w, 'editor_pegboard'):
            w = w.parent()

        self.mainframe = w if w is not None else parent

        self.config = config if config is not None else _config.Config.editor_pegboard
        self._init = False
        self.context = _context.GLContext(self)

        from . import camera as _camera
        self.camera = _camera.Camera(self)

        self._mouse_down_pos = None
        self._last_mouse_pos = None
        self._is_panning = False

        self._ref_count = 0
        self.size = None

        from . import mouse_handler as _mouse_handler
        self._mouse_handler = _mouse_handler.MouseHandlerPegBoard(self)

        from . import key_handler as _key_handler
        self._key_handler = _key_handler.KeyHandler(self)

        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

        self._grid = _grid.Grid(self)

        # Peg-board scene state -- see load_project()/add_anchor()/
        # remove_anchor() and _render_objects() below. self._pegboard_program
        # is compiled once the GL context exists (initializeGL);
        # self._anchors is now an incrementally-maintained live list of
        # objects.objectspeg.basepeg.BasePeg instances (one
        # per placed housing/splice/transition/bare-terminal) -- populated by
        # a full walk in load_project() (initial project-open) and kept
        # current afterward via add_anchor()/remove_anchor() (called from
        # ui.editor_pegboard.editor_pegboard.EditorPegBoardPanel.add_object/
        # remove_object), never by re-deriving the whole list from the DB.
        self._pegboard_program = None
        self._anchors: list["_basepeg.BasePeg"] = []

        # The project load_project() was last called with -- needed by the
        # Phase 3 drag-commit methods (commit_anchor_drag/
        # commit_waypoint_drag) so they can reach ptables without the
        # mouse handler having to thread a project reference through every
        # call. None until the first load_project() call.
        self._project = None

        # Phase 2 bundle-strand / bare-wire-strand state. Bundle strands
        # (self._bundle_strands) render live every frame straight off the
        # shared, pooled unit-cylinder VBO -- position/rotation/scale
        # uniforms recomputed fresh from each edge's current node
        # positions, no per-edge VBO of their own at all (see
        # _render_bundle_strands()). Bare-wire strands are always a single
        # straight segment (no bends), so they keep the simpler "build a
        # one-off flat-quad VBO per strand" approach -- the dataclass list
        # is cheap to rebuild in load_project() (no GL context needed),
        # but its GPU-side (vbo, material) pairs require a current GL
        # context to build, deferred to _render_objects() via the dirty
        # flag, mirroring load_project()'s own "always full rebuild, not
        # incremental" pattern.
        self._bundle_strands: list["_layout_graph.BundleStrand"] = []
        self._bare_wire_strands: list["_layout_graph.BareWireStrand"] = []
        self._bare_wire_strand_draws: list[tuple["_vbo.NonPooledVBOHandler", "_materials.GLMaterial"]] = []
        self._strand_draws_dirty = False

        # Phase 3 live node/edge graph -- the *same* PegboardNode/
        # PegboardEdge instances load_project() builds via
        # layout_graph.build_bundle_graph(), retained here (not thrown
        # away) so a drag can mutate a node's x/z in place and cheaply
        # find exactly which edges touch it (see edges_touching_node()/
        # drag_update_anchor()/drag_update_waypoint()) without ever
        # re-querying the database or rebuilding the graph mid-drag.
        # self._bundle_strands[i] always corresponds to self._edges[i]
        # (width/color only now -- position comes live from the edge's own
        # nodes at render time) -- see load_project() and
        # layout_graph.build_bundle_strands_for_edges() for how that 1:1
        # index correspondence is built and kept true. No dirty-edge
        # tracking is needed for bundle strands any more -- there's no
        # per-edge VBO to selectively update, so _render_bundle_strands()
        # simply reads every edge's current node positions fresh, every
        # frame, unconditionally.
        self._nodes: list["_layout_graph.PegboardNode"] = []
        self._edges: list["_layout_graph.PegboardEdge"] = []

        # Phase 3 "pull" drag mode bookkeeping -- every waypoint touched by
        # a live drag's propagation (see _propagate_pull()/
        # _record_drag_dirty()), so commit_drag() can persist all of them
        # exactly once on release, not just the one directly-dragged node.
        # Anchors need no equivalent list -- an anchor's position is a
        # live, DB-backed Point that already persists immediately on every
        # mutation (see _entity_set_pos()/drag_update_anchor()). Always
        # empty in "clamp" mode (nothing but the primary entity ever moves
        # there). Cleared by commit_drag() at the end of every drag.
        self._drag_dirty_waypoint_ids: list = []

        # Peg-board rotation gizmo state -- "angle mode" equivalent to the
        # 3D editor's RotationRings/Rings3D, but board-only (see
        # gl.canvas_pegboard.rotation_ring.PegboardRotationRing's module
        # docstring for why this is a standalone class, not a reuse of
        # those). self._rotation_gizmo_anchor is the anchor currently
        # showing its rotate ring, or None. self._rotation_gizmo is the
        # actual GPU-side gizmo -- built lazily (needs a current GL
        # context) the next time _render_objects() runs after
        # enter_rotation_mode(), mirroring self._strand_draws_dirty's
        # deferred-build pattern; self._rotation_gizmo_dirty flags that a
        # (re)build is pending. self._rotation_gizmo_degrees is the live,
        # in-progress rotation-in-degrees shown by the gizmo/anchor mesh
        # during a drag -- mutated in memory only until
        # commit_anchor_rotation() persists it on release, mirroring
        # drag_update_anchor()/commit_anchor_drag()'s "mutate in memory
        # during drag, commit once on release" discipline exactly.
        self._rotation_gizmo_anchor: "_basepeg.BasePeg | None" = None
        self._rotation_gizmo: "_rotation_ring.PegboardRotationRing | None" = None
        self._rotation_gizmo_dirty = False
        self._rotation_gizmo_degrees = 0.0

        # Phase 4 data-table overlays -- one PegboardTableWidget per anchor
        # point3d_id (or, for a transition, per populated branch's own
        # position3d_id -- see objectspeg.transition.Transition.
        # table_anchor_points). Repositioned/rescaled on every camera
        # change via Refresh() (see below); populated by load_project()/
        # add_anchor()/remove_anchor().
        self.tables_overlay = _tables_overlay.TablesOverlay(self)

        # In-progress table-drag leader line (see begin_table_drag()/
        # update_table_drag()/end_table_drag(), driven by
        # tables_overlay.PegboardTableWidget's title-strip drag handler) --
        # a flat quad, using the same build_strand_quad()/
        # NonPooledVBOHandler.update() in-place-respecify pattern bare-wire
        # strands still use (see _rebuild_strand_draws()) -- unlike bundle
        # strands (_render_bundle_strands()), this genuinely is its own
        # one-off VBO, since a table drag line has no shared/pooled shape
        # to reuse. None whenever no table drag is in progress.
        self._table_drag_anchor_pos: "_point.Point | None" = None
        self._table_drag_current_pos: "_point.Point | None" = None
        self._table_drag_line_draw: "tuple['_vbo.NonPooledVBOHandler', '_materials.GLMaterial'] | None" = None
        self._table_drag_line_dirty = False

        if size is not None:
            self.resize(size)

    # ------------------------------------------------------------------
    # Camera movement
    # ------------------------------------------------------------------

    def Zoom(self, dx: float, _=None):
        """Execute the zoom operation.

        :param dx: Zoom delta.
        :type dx: float
        :param _: Unused (kept for signature parity with Camera2D consumers).
        :type _: UNKNOWN
        """
        dx *= self.config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Pan(self, dx: float, dy: float) -> None:
        """Execute the pan operation.

        :param dx: Horizontal screen-pixel delta.
        :type dx: float
        :param dy: Vertical screen-pixel delta.
        :type dy: float
        """
        if self.config.pan.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if self.config.pan.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = self.config.pan.sensitivity
        self.camera.Pan(dx * sens, dy * sens)

    # ------------------------------------------------------------------
    # Grid / snap helpers
    # ------------------------------------------------------------------

    def snap_to_grid(self, world_pos: _point.Point) -> _point.Point:
        """Snap a world position to the current grid spacing.

        :param world_pos: Position to snap.
        :type world_pos: :class:`_point.Point`
        :returns: Snapped position (unchanged if grid snap is disabled).
        :rtype: :class:`_point.Point`
        """
        if not self.config.grid.snap:
            return world_pos

        manual_spacing = self.config.grid.manual_snap_spacing
        spacing = self._grid.grid_spacing if manual_spacing is None else manual_spacing

        return _point.Point(
            round(world_pos.x / spacing) * spacing,
            round(world_pos.y / spacing) * spacing,
        )

    def set_grid_snap(self, value) -> None:
        """Enable/disable snap-to-grid.

        :param value: New snap-to-grid state.
        :type value: UNKNOWN
        """
        self.config.grid.snap = bool(value)

    def set_grid_display(self, value) -> None:
        """Show/hide the reference grid.

        :param value: New grid-visibility state.
        :type value: UNKNOWN
        """
        self.config.grid.enabled = bool(value)
        self._grid.set(self.config.grid.enabled)
        self.update()

    # ------------------------------------------------------------------
    # Reference-counting context manager (Camera2D calls Refresh() on
    # focal-position change; ref-counting lets a caller batch several
    # camera moves and only repaint once)
    # ------------------------------------------------------------------

    def __enter__(self):
        """Enter the managed context."""
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        :param exc_type: Exception type, if any.
        :type exc_type: UNKNOWN
        :param exc_val: Exception value, if any.
        :type exc_val: UNKNOWN
        :param exc_tb: Exception traceback, if any.
        :type exc_tb: UNKNOWN
        """
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        """Repaint the canvas, unless a batching context is still open.

        Also the single choke point every camera move (pan/zoom) already
        funnels through -- reused here to reposition/rescale every visible
        data-table overlay (:meth:`tables_overlay.TablesOverlay.
        reposition_all`) whenever the camera changes, without needing a
        separate signal of its own.

        :param args: Unused, kept for call-site parity with wx-style Refresh.
        :type args: UNKNOWN
        :param kwargs: Unused, kept for call-site parity with wx-style Refresh.
        :type kwargs: UNKNOWN
        """
        if self._ref_count:
            return

        self.tables_overlay.reposition_all()
        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    def initializeGL(self):
        """One-time GL setup. Qt guarantees the context is already current here."""
        GL.glClearColor(0.9600, 0.9568, 0.9372, 1.0)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        GL.glDisable(GL.GL_DEPTH_TEST)

        if self.size:
            GL.glViewport(0, 0, self.size[0], self.size[1])

        self._setup_projection()
        self._grid.set(self.config.grid.enabled)

        self._pegboard_program = _shaders.compile_schematic2d_program()

    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize. Context is already current here."""
        self.size = (width, height)
        GL.glViewport(0, 0, width, height)
        self._setup_projection()

    def paintGL(self):
        """Render one frame. Context is already current here."""
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        self._setup_projection()
        self._grid.render(self.camera.distance)
        self._render_objects()
        # Qt handles SwapBuffers automatically.

    @staticmethod
    def _collect_anchors(project) -> list:
        """Walk every already-constructed housing/splice/transition/terminal
        row and collect its real, active ``objpeg``.

        Replaces the former ``layout_graph.build_anchors(project)`` bulk
        DB-driven rebuild: anchors are no longer independently derived here
        at all -- each placed part's ``ObjectBase`` subclass already built
        its own ``objpeg`` (a dedicated per-type
        ``objects.objectspeg.basepeg.BasePeg`` subclass instance for the 4
        anchor types, or a dedicated per-type ``objects.objectspeg.basepeg.
        BasePeg`` subclass instance for every other type -- never a single
        shared stub class) at construction time, exactly like ``obj2d``/
        ``obj3d``. This still needs a full walk at initial project-open
        time -- there is no other way to enumerate "everything already
        placed" at that moment -- but every subsequent add/remove goes
        through the incremental :meth:`add_anchor`/:meth:`remove_anchor`
        instead of ever calling this again.

        :param project: The currently open project (``mainframe.project``).
        :type project: :class:`harness_designer.objects.project.Project`
        :returns: One anchor per placed housing/splice/transition/bare
            terminal that currently has a real, active ``objpeg``.
        :rtype: list[:class:`~harness_designer.objects.objectspeg.basepeg.BasePeg`]
        """
        anchors = []
        tables = (
            project.ptables.pjt_housings_table,
            project.ptables.pjt_splices_table,
            project.ptables.pjt_transitions_table,
            project.ptables.pjt_terminals_table,
        )

        for table in tables:
            for row in table:
                obj = row.get_object()
                if obj is None:
                    continue

                objpeg = getattr(obj, 'objpeg', None)
                if objpeg is None or not objpeg.is_active:
                    continue

                anchors.append(objpeg)

        return anchors

    def load_project(self, project) -> None:
        """Build this canvas's anchor list from *project* and repaint.

        Called once a project is open and its 3D scene objects exist. Safe
        to call again later (e.g. on project reload) -- it always rebuilds
        the full anchor list from scratch via :meth:`_collect_anchors`. This
        is a DIFFERENT operation than the incremental :meth:`add_anchor`/
        :meth:`remove_anchor` used for every subsequent single-object
        add/remove (see ``ui.mainframe.MainFrame.add_object``/
        ``remove_object``, which no longer call this on every invocation).

        :param project: The currently open project (``mainframe.project``).
        :type project: :class:`harness_designer.objects.project.Project`
        """
        from . import layout_graph as _layout_graph

        # A fresh full rebuild replaces every anchor instance -- any active
        # rotation gizmo is bound to an anchor from the *old* list (and,
        # before this rebuild, potentially GPU buffers from a still-current
        # GL context), so it must be torn down here rather than left
        # dangling. exit_rotation_mode() is a no-op when no gizmo is active,
        # and safe to call without a current GL context (see its docstring).
        self.exit_rotation_mode()

        self._project = project

        self._anchors = self._collect_anchors(project)
        anchors_by_point3d_id = {
            anchor.point3d_id: anchor for anchor in self._anchors
        }

        # Bundle-graph code is unchanged except for where
        # anchors_by_point3d_id now comes from (self._anchors, above,
        # instead of layout_graph.build_anchors()'s return) -- build (and
        # retain) the live node/edge graph once here, then derive this
        # frame's strand list directly from self._edges
        # (build_bundle_strands_for_edges(), not the independent
        # build_bundle_strands()) so self._bundle_strands[i] always
        # corresponds to self._edges[i] -- the index correspondence
        # edges_touching_node()/drag_update_anchor()/
        # drag_update_waypoint() depend on to find "which strand-draw VBO
        # does this edge own" without a second graph walk.
        self._nodes, self._edges = _layout_graph.build_bundle_graph(
            project, anchors_by_point3d_id)
        self._bundle_strands = _layout_graph.build_bundle_strands_for_edges(
            project, self._edges)
        self._bare_wire_strands = _layout_graph.build_bare_wire_strands(project)

        # Data-table overlays -- a full rebuild, matching this method's own
        # "always full rebuild, not incremental" pattern (see add_anchor/
        # remove_anchor for the incremental path every subsequent single-
        # object add/remove takes instead).
        self.tables_overlay.clear()
        for anchor in self._anchors:
            self._ensure_tables_for_anchor(anchor)

        # Building the actual GPU-side bare-wire-strand VBOs needs a
        # current GL context, which isn't guaranteed at load_project()
        # call time -- deferred to _render_objects() (always
        # context-current inside paintGL()). Bundle strands need no such
        # deferred build at all any more -- see _render_bundle_strands().
        self._strand_draws_dirty = True

        self.update()

    def add_anchor(self, obj_pegboard: "_basepeg.BasePeg") -> None:
        """Incrementally register one anchor, without a full rebuild.

        Called by ``ui.editor_pegboard.editor_pegboard.EditorPegBoardPanel.add_object``
        whenever any object with a real (non-stub) ``obj_pegboard`` is added
        anywhere in the app -- this is what makes peg-board add genuinely
        incremental, matching ``editor2d``/``editor3d``, instead of the
        former unconditional ``load_project()`` bulk rebuild on every single
        ``mainframe.add_object`` call.

        :param obj_pegboard: The anchor to register.
        :type obj_pegboard: :class:`_basepeg.BasePeg`
        """
        if obj_pegboard is None or obj_pegboard in self._anchors:
            return

        self._anchors.append(obj_pegboard)
        self._ensure_tables_for_anchor(obj_pegboard)
        self.update()

    def remove_anchor(self, obj_pegboard: "_basepeg.BasePeg") -> None:
        """Incrementally unregister one anchor, without a full rebuild.

        Mirrors :meth:`add_anchor` -- called by
        ``ui.editor_pegboard.editor_pegboard.EditorPegBoardPanel.remove_object``.

        :param obj_pegboard: The anchor to unregister.
        :type obj_pegboard: :class:`_basepeg.BasePeg`
        """
        if obj_pegboard is None or obj_pegboard not in self._anchors:
            return

        self.tables_overlay.remove_tables_for_points(
            point3d_id for point3d_id, _x, _y, _label in obj_pegboard.table_anchor_points)

        self._anchors.remove(obj_pegboard)

        if self._rotation_gizmo_anchor is obj_pegboard:
            self.exit_rotation_mode()

        self.update()

    def _ensure_tables_for_anchor(self, anchor: "_basepeg.BasePeg") -> None:
        """Create/refresh every data-table overlay *anchor* needs.

        Most anchor types need exactly one (their own point3d_id) --
        ``objectspeg.transition.Transition`` needs one per populated
        branch (see :attr:`~objectspeg.basepeg.BasePeg.table_anchor_points`).
        No-op if no project is loaded yet (mirrors ``tables_overlay.
        TablesOverlay``'s own guards).

        :param anchor: The anchor to build table(s) for.
        :type anchor: :class:`_basepeg.BasePeg`
        """
        if self._project is None:
            return

        for point3d_id, world_x, world_z, label in anchor.table_anchor_points:
            rows = anchor.build_table_rows(self._project, point3d_id)
            self.tables_overlay.ensure_table(
                point3d_id, world_x, world_z, label, rows,
                anchor.table_include_cavity_columns)

    def center_on_object(self, obj) -> None:
        """Pan the camera so *obj*'s anchor is centered, keeping the
        current zoom/distance -- used by ``mainframe._set_selected()`` to
        bring a selection into view without disturbing the user's zoom.

        No-op if *obj* has no anchor on this canvas (not a peg-board-
        renderable part, or the anchor list hasn't been built yet).

        :param obj: The wrapper whose anchor should be centered.
        :type obj: :class:`harness_designer.objects.object_base.ObjectBase`
        """
        for anchor in self._anchors:
            if anchor.obj is obj:
                self.camera.x = anchor.position.x
                self.camera.y = anchor.position.z
                return

    @property
    def project(self):
        """Return the project :meth:`load_project` was last called with
        (``None`` before the first call) -- public read accessor for
        :attr:`_project`, used by ``tables_overlay`` so it doesn't need a
        second project reference threaded through separately.

        :rtype: :class:`harness_designer.objects.project.Project` | None
        """
        return self._project

    def begin_table_drag(self, anchor_world_pos: "_point.Point") -> None:
        """Start rendering a leader line from *anchor_world_pos* to
        wherever a table overlay is currently being dragged -- called by
        ``tables_overlay._TitleStrip.mousePressEvent``.

        :param anchor_world_pos: The dragged table's owning anchor point's
            world position (fixed for the duration of the drag).
        :type anchor_world_pos: :class:`_point.Point`
        """
        self._table_drag_anchor_pos = anchor_world_pos
        self._table_drag_current_pos = anchor_world_pos
        self._table_drag_line_dirty = True
        self.Refresh()

    def update_table_drag(self, table_world_pos: "_point.Point") -> None:
        """Update the leader line's table-side endpoint -- called on every
        mouse-move by ``tables_overlay._TitleStrip.mouseMoveEvent``.

        No-op if no table drag is in progress (defensive -- shouldn't
        happen given the caller's own press/release pairing).

        :param table_world_pos: The table's current world position.
        :type table_world_pos: :class:`_point.Point`
        """
        if self._table_drag_anchor_pos is None:
            return

        self._table_drag_current_pos = table_world_pos
        self._table_drag_line_dirty = True
        self.Refresh()

    def end_table_drag(self) -> None:
        """Stop rendering the drag leader line and release its GPU buffer
        -- called by ``tables_overlay._TitleStrip.mouseReleaseEvent``.
        """
        self._table_drag_anchor_pos = None
        self._table_drag_current_pos = None

        if self._table_drag_line_draw is not None:
            vbo_handler, _material = self._table_drag_line_draw
            vbo_handler.release()
            self._table_drag_line_draw = None

        self.Refresh()

    def _rebuild_table_drag_line(self) -> None:
        """(Re)build/update the GPU-side drag leader-line quad from
        :attr:`_table_drag_anchor_pos`/:attr:`_table_drag_current_pos`.

        A create-once/``NonPooledVBOHandler.update()``-thereafter pattern
        (its own one-off VBO, not shared/pooled -- see
        :attr:`_table_drag_line_draw`'s docstring) -- requires a current
        GL context, only ever called from :meth:`_render_objects`.
        """
        from . import strand_mesh as _strand_mesh

        packed, count = _strand_mesh.build_strand_quad(
            (self._table_drag_anchor_pos.x, self._table_drag_anchor_pos.z),
            (self._table_drag_current_pos.x, self._table_drag_current_pos.z),
            _TABLE_DRAG_LINE_WIDTH_MM)

        if self._table_drag_line_draw is None:
            vbo_handler = _vbo.NonPooledVBOHandler(packed, count)
            material = _materials.Generic(_color.Color(*_TABLE_DRAG_LINE_COLOR_RGB))
            self._table_drag_line_draw = (vbo_handler, material)
        else:
            vbo_handler, _existing_material = self._table_drag_line_draw
            vbo_handler.update(packed, count)

        self._table_drag_line_dirty = False

    @property
    def anchors(self) -> list["_basepeg.BasePeg"]:
        """Return the current Phase 1 static anchor list.

        Public read accessor for :attr:`_anchors` -- mirrors
        ``gl.canvas2d.canvas.Canvas.objects`` -- so
        ``MouseHandlerPegBoard`` can hit-test/select without reaching into
        a private attribute across module boundaries.

        :returns: Property value.
        :rtype: list[:class:`_basepeg.BasePeg`]
        """
        return self._anchors

    @property
    def nodes(self) -> list["_layout_graph.PegboardNode"]:
        """Return the current Phase 3 live node list.

        Public read accessor for :attr:`_nodes` (see :meth:`load_project`)
        so ``MouseHandlerPegBoard``/``handlers.pegboard_handler`` can
        hit-test waypoints without reaching into a private attribute.

        :returns: Property value.
        :rtype: list[:class:`_layout_graph.PegboardNode`]
        """
        return self._nodes

    @property
    def edges(self) -> list["_layout_graph.PegboardEdge"]:
        """Return the current Phase 3 live edge list.

        Public read accessor for :attr:`_edges` -- ``self._edges[i]``
        always corresponds to ``self._bundle_strands[i]`` (see
        :meth:`load_project`), which is what lets a strand-click hit-test
        (``handlers.pegboard_handler``) resolve directly to a bundle/
        length-budget without any extra lookup.

        :returns: Property value.
        :rtype: list[:class:`_layout_graph.PegboardEdge`]
        """
        return self._edges

    # ------------------------------------------------------------------
    # Phase 3: drag-to-reposition (local per-edge length clamp)
    # ------------------------------------------------------------------

    def edges_touching_node(self, *, anchor=None,
                             waypoint_id: int = None) -> list:
        """Return every live edge touching an anchor or waypoint node.

        Matches by node *identity* (``id(node)``), not dataclass ``==``
        equality (:class:`~harness_designer.gl.canvas_pegboard.layout_graph.PegboardNode`
        is a plain, non-frozen dataclass -- its generated ``__eq__`` does a
        field-by-field comparison, which is not what "is this the same
        node" means here). An anchor shared by more than one bundle chain
        gets one distinct :class:`PegboardNode` instance per chain (see
        ``layout_graph._resolve_chain_endpoint``), all wrapping the exact
        same :class:`_basepeg.BasePeg` object -- so matching by ``node.anchor
        is anchor`` (rather than trying to track a single canonical node
        per anchor) is what makes dragging a multi-bundle anchor correctly
        pick up every chain it participates in.

        No database access and no graph rebuild -- a plain scan of the
        already-live :attr:`_nodes`/:attr:`_edges` lists, safe to call once
        per drag-arm (not per mouse-move).

        :param anchor: The dragged anchor, or ``None`` when dragging a
            waypoint instead.
        :type anchor: :class:`_basepeg.BasePeg` | None
        :param waypoint_id: The dragged waypoint's row id, or ``None``
            when dragging an anchor instead.
        :type waypoint_id: int | None
        :returns: ``(edge_index, edge, neighbor_node)`` triples --
            *edge_index* is this edge's index into :attr:`_edges` (and
            therefore also :attr:`_bundle_strands`), *neighbor_node* is
            whichever of the edge's two nodes is *not* the dragged one.
        :rtype: list[tuple[int, :class:`_layout_graph.PegboardEdge`, :class:`_layout_graph.PegboardNode`]]
        """
        match_ids = set()
        for node in self._nodes:
            if anchor is not None and node.anchor is anchor:
                match_ids.add(id(node))
            elif waypoint_id is not None and node.waypoint_id == waypoint_id:
                match_ids.add(id(node))

        touching = []
        for index, edge in enumerate(self._edges):
            if id(edge.node_a) in match_ids:
                touching.append((index, edge, edge.node_b))
            elif id(edge.node_b) in match_ids:
                touching.append((index, edge, edge.node_a))

        return touching

    @staticmethod
    def _clamp_to_edge(cand_x: float, cand_z: float, neighbor_x: float,
                        neighbor_z: float, max_length_mm: float) -> tuple:
        """Clamp ``(cand_x, cand_z)`` so its distance from
        ``(neighbor_x, neighbor_z)`` never exceeds *max_length_mm*.

        Direct implementation of the plan's locked-in local-clamp
        pseudocode (``tranquil-orbiting-spindle.md``, "Drag-to-reposition
        (local clamp)") -- applied once per touching edge, independently,
        never a simultaneous/relaxed solve across every edge at once.

        :returns: The (possibly clamped) candidate position.
        :rtype: tuple[float, float]
        """
        dx = cand_x - neighbor_x
        dz = cand_z - neighbor_z
        dist = math.hypot(dx, dz)

        if dist <= max_length_mm or dist < 1e-9:
            return cand_x, cand_z

        scale = max_length_mm / dist
        return neighbor_x + dx * scale, neighbor_z + dz * scale

    def _apply_local_clamp(self, cand_x: float, cand_z: float,
                            touching: list) -> tuple:
        """Apply :meth:`_clamp_to_edge` for every ``(index, edge,
        neighbor)`` in *touching*, in sequence -- each edge clamped
        independently against the *previous* clamp's result, matching the
        plan's explicit ``for edge in edges_touching(node): ...`` loop
        (not a simultaneous solve).
        """
        for _index, edge, neighbor in touching:
            cand_x, cand_z = self._clamp_to_edge(
                cand_x, cand_z, neighbor.x, neighbor.z, edge.max_length_mm)

        return cand_x, cand_z

    def _entity_for_node(self, node: "_layout_graph.PegboardNode") -> tuple:
        """Return the stable "moving entity" a :class:`PegboardNode` maps to.

        A :class:`PegboardNode` is a per-chain snapshot -- an anchor shared
        by more than one bundle gets one distinct node instance per chain
        (see :meth:`edges_touching_node`'s docstring), so *node* identity is
        not what "one draggable thing" means. The entity is instead
        ``('anchor', anchor)`` (matched by ``is``, since
        :class:`~_basepeg.BasePeg` is a plain, non-frozen
        dataclass and therefore unhashable/unsafe to `==`-compare for this
        purpose) or ``('waypoint', waypoint_id)`` (matched by value -- a
        waypoint's id is already a stable, hashable identity).

        :param node: The node to resolve.
        :type node: :class:`_layout_graph.PegboardNode`
        :returns: ``('anchor', anchor)`` or ``('waypoint', waypoint_id)``.
        :rtype: tuple
        """
        if node.anchor is not None:
            return ('anchor', node.anchor)
        return ('waypoint', node.waypoint_id)

    @staticmethod
    def _same_entity(a: tuple, b: tuple) -> bool:
        """Return whether entities *a* and *b* (see :meth:`_entity_for_node`)
        refer to the same draggable thing."""
        if a[0] != b[0]:
            return False
        if a[0] == 'anchor':
            return a[1] is b[1]
        return a[1] == b[1]

    def _entity_pos(self, entity: tuple) -> tuple:
        """Return an entity's current live ``(x, z)`` position."""
        if entity[0] == 'anchor':
            anchor = entity[1]
            return anchor.position.x, anchor.position.z

        waypoint_id = entity[1]
        for node in self._nodes:
            if node.waypoint_id == waypoint_id:
                return node.x, node.z

        return None

    def _entity_set_pos(self, entity: tuple, x: float, z: float) -> None:
        """Set an entity's live ``(x, z)`` position, keeping every
        :class:`PegboardNode` wrapping it (an anchor may back several, one
        per chain -- see :meth:`_entity_for_node`) in sync.

        For an anchor, this writes straight to the live, bindable
        ``anchor.position`` -- which persists immediately via its own
        bound DB-layer callback (``PositionPegMixin``), same "no batching"
        discipline ``position3d``/``position2d`` already use. There is no
        separate commit step for anchors anymore (see
        :meth:`drag_update_anchor`/:meth:`commit_drag`).
        """
        if entity[0] == 'anchor':
            anchor = entity[1]
            anchor.position.x = x
            anchor.position.z = z
            for node in self._nodes:
                if node.anchor is anchor:
                    node.x = x
                    node.z = z
            return

        waypoint_id = entity[1]
        for node in self._nodes:
            if node.waypoint_id == waypoint_id:
                node.x = x
                node.z = z

    def _entity_touching_edges(self, entity: tuple) -> list:
        """Return ``edges_touching_node()`` for an entity (see
        :meth:`_entity_for_node`)."""
        if entity[0] == 'anchor':
            return self.edges_touching_node(anchor=entity[1])
        return self.edges_touching_node(waypoint_id=entity[1])

    def _propagate_pull(self, start_entity: tuple, cand_x: float,
                         cand_z: float) -> list:
        """"Pull" drag mode: move *start_entity* to ``(cand_x, cand_z)``
        unclamped, then recursively pull any neighbor whose touching edge
        has gone taut (distance > ``edge.max_length_mm``) toward it,
        maintaining that edge at exactly its budgeted length -- like
        dragging one end of a taut, inextensible rope: past the taut
        point, the far end comes along instead of the drag simply
        stopping (which is what "clamp" mode does instead -- see
        :meth:`_apply_local_clamp`).

        A breadth-first walk outward from *start_entity*, each pulled
        neighbor becoming the next entity whose *own* other edges get
        checked -- a taut edge propagates the pull further down the chain;
        a slack edge (``dist <= max_length_mm``) absorbs it and stops that
        branch. ``visited`` (checked via :meth:`_same_entity`, since
        entities aren't safely hashable) prevents revisiting an entity --
        necessary because an anchor participating in more than one bundle
        chain can otherwise be reached again from a different edge and
        re-processed pointlessly (bundle chains are linear, not cyclic,
        but a multi-bundle anchor hub makes the overall graph a tree/DAG,
        not strictly a simple path).

        :param start_entity: The dragged entity (see :meth:`_entity_for_node`).
        :type start_entity: tuple
        :param cand_x: Unclamped candidate world X for *start_entity*.
        :type cand_x: float
        :param cand_z: Unclamped candidate world Z for *start_entity*.
        :type cand_z: float
        :returns: Every entity whose position changed (including
            *start_entity*). Bundle-strand rendering needs no equivalent
            "which edges changed" tracking any more -- it reads every
            edge's live node positions fresh every frame (see
            :meth:`_render_bundle_strands`).
        :rtype: list[tuple]
        """
        self._entity_set_pos(start_entity, cand_x, cand_z)

        visited = [start_entity]
        moved = [start_entity]
        frontier = [start_entity]

        while frontier:
            entity = frontier.pop()
            ex, ez = self._entity_pos(entity)

            for _index, edge, neighbor_node in self._entity_touching_edges(entity):
                neighbor_entity = self._entity_for_node(neighbor_node)
                if any(self._same_entity(neighbor_entity, v) for v in visited):
                    continue

                nx, nz = self._entity_pos(neighbor_entity)
                dist = math.hypot(nx - ex, nz - ez)

                if dist <= edge.max_length_mm:
                    # Slack -- this edge absorbs the pull; the neighbor
                    # doesn't move and the pull doesn't propagate past it.
                    continue

                scale = edge.max_length_mm / dist if dist > 1e-9 else 0.0
                new_nx = ex + (nx - ex) * scale
                new_nz = ez + (nz - ez) * scale
                self._entity_set_pos(neighbor_entity, new_nx, new_nz)

                visited.append(neighbor_entity)
                moved.append(neighbor_entity)
                frontier.append(neighbor_entity)

        return moved

    def _record_drag_dirty(self, entity: tuple) -> None:
        """Remember a *waypoint* entity as needing a database write on
        release (see :meth:`commit_drag`) -- de-duplicated so a waypoint
        touched by several mouse-moves during one drag is only committed
        once.

        Anchors are NOT tracked here anymore: an anchor's position is a
        live, DB-backed ``Point`` (``PositionPegMixin``) that persists
        immediately on every mutation (see :meth:`_entity_set_pos`), same
        "no batching" discipline ``position3d``/``position2d`` already use
        for live dragging -- there is nothing left to commit for an
        anchor by the time a drag ends. Waypoints have no such live
        DB-backed value (``PegboardNode.x``/``.z`` are plain floats, no
        binding) -- they still need the deferred commit-on-release this
        method feeds.
        """
        if entity[0] != 'anchor':
            waypoint_id = entity[1]
            if waypoint_id not in self._drag_dirty_waypoint_ids:
                self._drag_dirty_waypoint_ids.append(waypoint_id)

    def drag_update_anchor(self, anchor: "_basepeg.BasePeg",
                            cand_x: float, cand_z: float,
                            touching: list) -> None:
        """Move *anchor* to ``(cand_x, cand_z)`` during a live drag.

        Behavior depends on ``self.config.drag.mode``: "clamp" (default)
        stops *anchor* itself at each touching edge's ``max_length_mm``
        boundary, exactly as before (see :meth:`_apply_local_clamp`).
        "pull" never clamps *anchor* itself -- instead any neighbor whose
        edge goes taut is pulled along, recursively (see
        :meth:`_propagate_pull`).

        Writes straight to ``anchor.position`` -- a live, DB-backed
        ``Point`` that persists immediately via its own bound callback
        (``PositionPegMixin``), same as every other live 3D/2D drag in
        this codebase already does (no deferred commit for anchors, see
        :meth:`_record_drag_dirty`'s docstring). Also keeps every
        :class:`PegboardNode` wrapping any moved anchor in sync and
        requests a repaint -- no GPU calls happen here directly, and no
        dirty-edge bookkeeping is needed at all: :meth:`_render_objects`
        re-reads every edge's live node positions fresh every single
        frame (see :meth:`_render_bundle_strands`).

        :param anchor: The anchor being dragged.
        :type anchor: :class:`_basepeg.BasePeg`
        :param cand_x: Unclamped candidate world X (already grid-snapped
            by the caller if applicable).
        :type cand_x: float
        :param cand_z: Unclamped candidate world Z.
        :type cand_z: float
        :param touching: This anchor's touching edges, from
            :meth:`edges_touching_node` (computed once at drag-arm time,
            not rebuilt here) -- only used in "clamp" mode.
        :type touching: list
        """
        if self.config.drag.mode == 'pull':
            moved = self._propagate_pull(('anchor', anchor), cand_x, cand_z)
            for entity in moved:
                self._record_drag_dirty(entity)
        else:
            cand_x, cand_z = self._apply_local_clamp(cand_x, cand_z, touching)

            anchor.position.x = cand_x
            anchor.position.z = cand_z

            for node in self._nodes:
                if node.anchor is anchor:
                    node.x = cand_x
                    node.z = cand_z

        self.update()

    def drag_update_waypoint(self, node: "_layout_graph.PegboardNode",
                              cand_x: float, cand_z: float,
                              touching: list) -> None:
        """Move a waypoint *node* to ``(cand_x, cand_z)`` during a live
        drag -- in-memory only, no database write (see :meth:`commit_drag`
        for that).

        Behavior depends on ``self.config.drag.mode`` -- see
        :meth:`drag_update_anchor`'s docstring (identical mode semantics,
        applied to a waypoint entity instead of an anchor entity).

        :param node: The waypoint node being dragged.
        :type node: :class:`_layout_graph.PegboardNode`
        :param cand_x: Unclamped candidate world X (already grid-snapped
            by the caller if applicable).
        :type cand_x: float
        :param cand_z: Unclamped candidate world Z.
        :type cand_z: float
        :param touching: This waypoint's touching edges, from
            :meth:`edges_touching_node` (computed once at drag-arm time)
            -- only used in "clamp" mode.
        :type touching: list
        """
        if self.config.drag.mode == 'pull':
            moved = self._propagate_pull(
                ('waypoint', node.waypoint_id), cand_x, cand_z)
            for entity in moved:
                self._record_drag_dirty(entity)
        else:
            cand_x, cand_z = self._apply_local_clamp(cand_x, cand_z, touching)

            node.x = cand_x
            node.z = cand_z

            self._record_drag_dirty(('waypoint', node.waypoint_id))

        self.update()

    def commit_waypoint_drag(self, node: "_layout_graph.PegboardNode") -> None:
        """Persist a waypoint *node*'s current position to its existing
        ``pjt_points_peg`` row.

        The row already exists by the time this is called -- either from
        a previous drag or from ``handlers.pegboard_handler`` creating it
        at click time -- so this never inserts, only updates.

        :param node: The waypoint node whose final position to persist.
        :type node: :class:`_layout_graph.PegboardNode`
        """
        if self._project is None or node.waypoint_id is None:
            return

        row = self._project.ptables.pjt_points_peg_table[node.waypoint_id]
        row.x = node.x
        row.z = node.z

    def commit_waypoint_drag_by_id(self, waypoint_id: int) -> None:
        """Persist a waypoint by its row id (see :meth:`commit_waypoint_drag`)
        without requiring a live :class:`PegboardNode` reference -- used by
        :meth:`commit_drag` for "pull"-mode neighbors that were never
        directly armed for drag.

        :param waypoint_id: The waypoint row id whose final position to persist.
        :type waypoint_id: int
        """
        if self._project is None:
            return

        for node in self._nodes:
            if node.waypoint_id == waypoint_id:
                row = self._project.ptables.pjt_points_peg_table[waypoint_id]
                row.x = node.x
                row.z = node.z
                return

    def commit_drag(self, primary_anchor=None, primary_node=None) -> None:
        """Persist every waypoint moved during the just-finished drag,
        exactly once each, on mouse release.

        Anchors need nothing here anymore: an anchor's position is a
        live, DB-backed ``Point`` that already persisted immediately on
        every mutation during the drag (see
        :meth:`drag_update_anchor`/:meth:`_entity_set_pos`) -- accepting
        *primary_anchor* as a parameter is kept only so
        ``mouse_handler.py``'s existing call shape doesn't need to
        special-case "was this an anchor or a waypoint drag".

        Waypoints have no live DB-backed value of their own
        (``PegboardNode.x``/``.z`` are plain floats), so they still need
        the deferred commit-on-release this method performs -- in "clamp"
        mode that's just *primary_node*; in "pull" mode it also includes
        every waypoint the pull propagated to (see
        :meth:`_propagate_pull`/:meth:`_record_drag_dirty`, accumulated in
        :attr:`_drag_dirty_waypoint_ids` since the drag was armed).

        Clears the dirty-drag bookkeeping afterward so the next drag
        starts fresh.

        Finally, every waypoint this drag touched (directly dragged, or
        pulled along in "pull" mode) is checked for having become
        collinear with its two neighbors and removed if so -- see
        :meth:`_remove_collinear_waypoints`.

        :param primary_anchor: The anchor directly armed for drag, if
            any -- accepted for call-shape parity, otherwise unused.
        :type primary_anchor: :class:`_basepeg.BasePeg` | None
        :param primary_node: The waypoint node directly armed for drag, if any.
        :type primary_node: :class:`_layout_graph.PegboardNode` | None
        """
        touched_waypoint_ids = set(self._drag_dirty_waypoint_ids)

        if primary_node is not None:
            self.commit_waypoint_drag(primary_node)
            touched_waypoint_ids.add(primary_node.waypoint_id)

        for waypoint_id in self._drag_dirty_waypoint_ids:
            if primary_node is None or waypoint_id != primary_node.waypoint_id:
                self.commit_waypoint_drag_by_id(waypoint_id)

        self._drag_dirty_waypoint_ids.clear()

        self._remove_collinear_waypoints(touched_waypoint_ids)

    # ------------------------------------------------------------------
    # Collinear-waypoint auto-removal (drag release only)
    # ------------------------------------------------------------------

    _COLLINEAR_TOLERANCE_MM = 2.0

    @staticmethod
    def _perpendicular_distance_mm(px: float, pz: float, ax: float, az: float,
                                    bx: float, bz: float) -> float:
        """Return the perpendicular distance from ``(px, pz)`` to the
        infinite line through ``(ax, az)``-``(bx, bz)``.

        Falls back to plain point-to-point distance when the two line
        points coincide (degenerate line), rather than dividing by zero.
        """
        ab_x, ab_z = bx - ax, bz - az
        length = math.hypot(ab_x, ab_z)

        if length < 1e-9:
            return math.hypot(px - ax, pz - az)

        ap_x, ap_z = px - ax, pz - az
        return abs(ab_x * ap_z - ab_z * ap_x) / length

    def _remove_collinear_waypoints(self, waypoint_ids: set) -> None:
        """Remove every waypoint in *waypoint_ids* that now sits (within
        :attr:`_COLLINEAR_TOLERANCE_MM`) on the straight line between its
        two neighboring chain nodes -- called once, on drag release
        (:meth:`commit_drag`), for every waypoint the just-finished drag
        touched (directly dragged, or pulled along in "pull" mode).

        Deliberately never checked mid-drag -- a waypoint straightening
        out is exactly the gesture that should remove it, but only once
        the user has settled on that position, not the instant it
        transiently passes through collinear on the way somewhere else.

        Every candidate's collinearity is evaluated against the graph as
        it stood *before* any removal in this same pass, so removing one
        waypoint can never affect whether another candidate in the same
        batch gets removed. Triggers exactly one full graph rebuild
        (:meth:`load_project`) at the end if anything was actually
        removed -- never one rebuild per removal.

        :param waypoint_ids: Every waypoint touched by the just-finished drag.
        :type waypoint_ids: set[int]
        """
        if self._project is None or not waypoint_ids:
            return

        to_remove = []

        for waypoint_id in waypoint_ids:
            touching = self.edges_touching_node(waypoint_id=waypoint_id)
            if len(touching) != 2:
                # Not an interior point with exactly two neighbors (e.g.
                # already removed earlier this same pass via a shared
                # bundle, or a genuine data oddity) -- nothing to check.
                continue

            node = next((n for n in self._nodes if n.waypoint_id == waypoint_id), None)
            if node is None:
                continue

            (_i1, _e1, neighbor_a), (_i2, _e2, neighbor_b) = touching

            distance = self._perpendicular_distance_mm(
                node.x, node.z, neighbor_a.x, neighbor_a.z, neighbor_b.x, neighbor_b.z)

            if distance <= self._COLLINEAR_TOLERANCE_MM:
                to_remove.append(waypoint_id)

        if not to_remove:
            return

        points_table = self._project.ptables.pjt_points_peg_table

        for waypoint_id in to_remove:
            row = points_table[waypoint_id]
            bundle_id = row.bundle_id
            removed_idx = row.idx

            row.delete()

            for other in points_table.for_bundle(bundle_id):
                if other.idx > removed_idx:
                    other.idx = other.idx - 1

        self.load_project(self._project)

    def begin_drag(self) -> None:
        """Reset "pull"-mode dirty bookkeeping at the start of a new drag.

        Defensive: :meth:`commit_drag` already clears
        :attr:`_drag_dirty_waypoint_ids` at the end of every completed
        drag, so this is normally a no-op -- but calling it whenever a
        drag is armed (``mouse_handler.on_left_down``'s anchor-arm branch,
        :meth:`arm_waypoint_drag`) guarantees a stale entry from some
        earlier drag that never reached :meth:`commit_drag` (e.g. an
        interrupted gesture) can never bleed into the next one.
        """
        self._drag_dirty_waypoint_ids.clear()

    def arm_waypoint_drag(self, node: "_layout_graph.PegboardNode") -> None:
        """Forward to the mouse handler to arm a continuous drag for
        *node*.

        Used by ``handlers.pegboard_handler.AddWaypointHandler`` right
        after it creates a brand-new waypoint from a click on a bundle
        strand, so the user can keep fine-tuning its position with the
        mouse before releasing -- exactly like
        ``handlers.bundle_layout_handler.AddBundleLayoutHandler`` does for
        3D bundle layouts.

        :param node: The newly-created waypoint node to arm a drag for.
        :type node: :class:`_layout_graph.PegboardNode`
        """
        self._mouse_handler.arm_waypoint_drag(node)

    # ------------------------------------------------------------------
    # Rotation gizmo lifecycle (board-plane-only spin -- see
    # gl.canvas_pegboard.rotation_ring.PegboardRotationRing)
    # ------------------------------------------------------------------

    @property
    def rotation_gizmo_anchor(self) -> "_basepeg.BasePeg | None":
        """Return the anchor currently showing its rotate ring, or ``None``.

        Public read accessor for :attr:`_rotation_gizmo_anchor` so
        ``MouseHandlerPegBoard`` can tell whether "rotation mode" is active
        without reaching into a private attribute.

        :returns: Property value.
        :rtype: :class:`_basepeg.BasePeg` | None
        """
        return self._rotation_gizmo_anchor

    @property
    def rotation_gizmo_degrees(self) -> float:
        """Return the active gizmo's live, in-progress rotation, in degrees.

        Public read accessor for :attr:`_rotation_gizmo_degrees` -- used by
        ``MouseHandlerPegBoard`` as the starting value when a handle drag
        is armed (mirrors ``gl.canvas3d.rotation_rings.DragRotate.
        start_value``, read live off the tracked object's own Euler angle
        at drag-arm time) and again to persist the final value on release.

        :returns: Property value.
        :rtype: float
        """
        return self._rotation_gizmo_degrees

    def enter_rotation_mode(self, anchor: "_basepeg.BasePeg") -> None:
        """Show the rotate-ring gizmo for *anchor*.

        Seeds :attr:`_rotation_gizmo_degrees` from *anchor*'s live
        ``anchor.angle.y``. The actual GPU-side gizmo is built lazily by
        :meth:`_render_objects` (needs a current GL context) -- this only
        flags the pending build (:attr:`_rotation_gizmo_dirty`), mirroring
        :attr:`_strand_draws_dirty`'s deferred-build pattern.

        A no-op if *anchor* is already the active gizmo's target. Any
        previously active gizmo (for a different anchor) is exited first.

        :param anchor: The anchor to show the rotate ring for.
        :type anchor: :class:`_basepeg.BasePeg`
        """
        if self._rotation_gizmo_anchor is anchor:
            return

        self.exit_rotation_mode()

        self._rotation_gizmo_anchor = anchor
        self._rotation_gizmo_degrees = float(anchor.angle.y)
        self._rotation_gizmo_dirty = True
        self.update()

    def exit_rotation_mode(self) -> None:
        """Hide the rotate-ring gizmo, releasing its GL buffers.

        Safe to call whether or not a gizmo is currently active (a no-op
        when it isn't), and safe to call from outside ``paintGL()`` (e.g.
        ``load_project()``, ``mouse_handler.py``) -- the release is wrapped
        in ``with self.context:`` so it acquires the GL context itself
        rather than assuming one is already current, mirroring
        ``gl.canvas3d.rotation_rings.Rings3D.detach()``'s same defensive
        acquire-before-release pattern.
        """
        if self._rotation_gizmo is not None:
            with self.context:
                self._rotation_gizmo.release()
            self._rotation_gizmo = None

        self._rotation_gizmo_anchor = None
        self._rotation_gizmo_dirty = False
        self.update()

    def update_rotation_drag(self, rotation_deg: float) -> None:
        """Update the live, in-progress rotation during a drag.

        Updates :attr:`_rotation_gizmo_degrees` (read by
        :meth:`_render_objects` to orient the gizmo itself) and writes
        straight to the target anchor's live ``anchor.angle.y`` -- a
        live, DB-backed ``Angle`` (``AnglePegMixin``) that persists
        immediately via its own bound callback, same "no batching"
        discipline ``angle3d``/``angle2d`` already use for live rotation
        dragging (a real SQLite write on every mouse-move, exactly like
        those). This alone is enough to make the anchor's mesh visibly
        spin along with the gizmo every frame -- ``BasePeg._update_angle``
        (bound to the same ``Angle``) recomputes the OBB/AABB and repaints
        on every mutation.

        A no-op if no rotation gizmo is currently active.

        :param rotation_deg: The new live rotation, in degrees.
        :type rotation_deg: float
        """
        anchor = self._rotation_gizmo_anchor
        if anchor is None:
            return

        self._rotation_gizmo_degrees = rotation_deg
        anchor.angle.y = rotation_deg

        self.update()

    def rotation_gizmo_handle_world_pos(self) -> "_point.Point | None":
        """Return the active gizmo's grab handle world position, or ``None``.

        ``None`` when no rotation gizmo is active, or when one is active
        but not yet built (the frame between :meth:`enter_rotation_mode`
        and the next :meth:`_render_objects` call) -- ``mouse_handler.py``
        treats either case as "nothing to hit-test".

        :returns: Handle world position (``.y`` stands in for world Z, same
            convention as every other peg-board world-position value), or
            ``None``.
        :rtype: :class:`_point.Point` | None
        """
        if self._rotation_gizmo is None or self._rotation_gizmo_anchor is None:
            return None

        return self._rotation_gizmo.handle_world_pos(self._rotation_gizmo_degrees)

    def _pegboard_projection_matrix(self) -> np.ndarray:
        """Build the orthographic projection matrix for the schematic2d
        shader, matching :meth:`_setup_projection`'s legacy
        ``glOrtho``/``glMatrixMode`` bounds exactly (same
        ``camera.distance``/``camera.x``/``camera.y``/``size`` inputs,
        same ``near=-1, far=1``).

        :returns: Row-major 4x4 orthographic projection matrix.
        :rtype: numpy.ndarray
        """
        width, height = self.size
        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height
        near, far = -1.0, 1.0

        return np.array([
            [2.0 / (right - left), 0.0, 0.0, -(right + left) / (right - left)],
            [0.0, 2.0 / (top - bottom), 0.0, -(top + bottom) / (top - bottom)],
            [0.0, 0.0, -2.0 / (far - near), -(far + near) / (far - near)],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

    @staticmethod
    def _release_strand_draws(draws: list) -> None:
        """Release the GL buffers backing one bare-wire-strand draw list.

        Called before rebuilding so repeated :meth:`load_project` calls
        (project reload) don't leak GPU buffers -- mirrors the "release
        before replace" discipline ``NonPooledVBOHandler``/``gl.vbo``
        already expects of its callers.
        """
        for vbo_handler, _material in draws:
            vbo_handler.release()

    @staticmethod
    def _build_strand_draws(strands: list) -> list:
        """Build one ``(NonPooledVBOHandler, Generic material)`` pair per
        bare-wire-strand dataclass, via ``strand_mesh.build_strand_quad``.

        Bare-wire strands only -- bundle strands render live off the
        shared cylinder VBO instead (see :meth:`_render_bundle_strands`),
        needing no per-edge VBO of their own. A bare-wire strand is always
        a single straight segment (bundle-exit point to a bare terminal,
        never bent), so a one-off CPU-built quad per strand is fine.

        Requires a current GL context (``NonPooledVBOHandler.__init__``
        calls ``glGenBuffers``/``glBufferData``) -- only ever called from
        :meth:`_render_objects`, which always runs inside ``paintGL()``.
        """
        from . import strand_mesh as _strand_mesh

        draws = []
        for strand in strands:
            packed, count = _strand_mesh.build_strand_quad(
                (strand.x1, strand.z1), (strand.x2, strand.z2), strand.width)

            vbo_handler = _vbo.NonPooledVBOHandler(packed, count)
            material = _materials.Generic(strand.color)
            draws.append((vbo_handler, material))

        return draws

    def _rebuild_strand_draws(self) -> None:
        """(Re)build the GPU-side bare-wire-strand draw list from the
        current ``self._bare_wire_strands`` dataclass list.

        Old GPU buffers are always released first (see
        :meth:`_release_strand_draws`) -- an unconditional full rebuild,
        matching the anchor list's own "always full rebuild, not
        incremental" Phase 1 pattern rather than diffing strand lists.
        """
        self._release_strand_draws(self._bare_wire_strand_draws)
        self._bare_wire_strand_draws = self._build_strand_draws(self._bare_wire_strands)

        self._strand_draws_dirty = False

    def _rebuild_rotation_gizmo(self) -> None:
        """(Re)build the GPU-side rotation-ring gizmo for whichever anchor
        is currently in "rotation mode" (:attr:`_rotation_gizmo_anchor`).

        Old GL buffers are always released first (mirrors
        :meth:`_release_strand_draws`'s "release before replace"
        discipline). A no-op build (gizmo left ``None``) if no anchor is
        currently in rotation mode -- can happen if
        :meth:`exit_rotation_mode` raced this call, though in practice both
        only ever run on the GUI thread. Requires a current GL context --
        only ever called from :meth:`_render_objects`.
        """
        from . import rotation_ring as _rotation_ring

        if self._rotation_gizmo is not None:
            self._rotation_gizmo.release()
            self._rotation_gizmo = None

        anchor = self._rotation_gizmo_anchor
        if anchor is not None:
            self._rotation_gizmo = _rotation_ring.PegboardRotationRing(anchor)

        self._rotation_gizmo_dirty = False

    def _render_strand_draws(self, draws: list) -> None:
        """Render one bare-wire-strand draw list under the already-bound
        ``self._pegboard_program``.

        Each strand's world-space XZ geometry is already baked directly
        into its vertices by ``strand_mesh.build_strand_quad`` -- so,
        unlike anchors (or bundle-strand cylinders, see
        :meth:`_render_bundle_strands`), no per-strand
        ``objectPosition``/``objectRotation`` offset is needed: identity
        transform (position at the world origin, identity quaternion,
        unit scale) reuses the exact same schematic2d uniform contract
        anchors already use, just as a no-op. ``normalMode`` is left at
        "face" (0) -- a flat quad's smooth and face normals are identical
        (both hardcoded ``(0, 1, 0)`` by ``build_strand_quad``), so it
        makes no visual difference.

        :param draws: ``(vbo, material)`` pairs -- ``self._bare_wire_strand_draws``.
        :type draws: list[tuple[:class:`_vbo.NonPooledVBOHandler`, :class:`_materials.GLMaterial`]]
        """
        pos_loc = GL.glGetUniformLocation(self._pegboard_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(self._pegboard_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(self._pegboard_program, "objectScale")
        normal_loc = GL.glGetUniformLocation(self._pegboard_program, "normalMode")

        GL.glUniform3f(pos_loc, 0.0, 0.0, 0.0)
        GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
        GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)
        GL.glUniform1i(normal_loc, 0)

        for vbo_handler, material in draws:
            material.set(self._pegboard_program)
            vbo_handler.render()

    def _render_bundle_strands(self) -> None:
        """Render every live bundle-graph edge as the shared, pooled unit
        cylinder VBO (``shapes.cylinder.create_vbo``), GPU-instanced
        purely via ``objectPosition``/``objectRotation``/``objectScale``
        uniforms -- no per-edge VBO of any kind, built, updated, or
        released. Position/rotation/length come fresh from
        ``strand_mesh.cylinder_placement()`` against each edge's *live*
        node positions (``PegboardNode.x``/``.z``, already kept current by
        ``drag_update_anchor``/``drag_update_waypoint``/
        ``_propagate_pull``), so this needs no dirty-edge tracking at all
        -- unconditionally correct every single frame, drag or not.

        A sphere (``shapes.sphere.create_vbo``) is placed at every
        interior *waypoint* node touched by 2+ edges, to visually join
        consecutive cylinder segments at a bend -- a flat-ended cylinder
        alone leaves a gap on the outside of a bend and an overlap on the
        inside. Anchor nodes need no such joint: a housing/splice/
        transition/bare-terminal already has its own real mesh sitting
        exactly there, which already covers the seam.

        Requires a current GL context and ``self._pegboard_program`` to
        already be bound -- only ever called from :meth:`_render_objects`.
        """
        if not self._edges:
            return

        from ...shapes import cylinder as _cylinder
        from ...shapes import sphere as _sphere
        from . import strand_mesh as _strand_mesh

        cylinder_vbo = _cylinder.create_vbo()
        sphere_vbo = _sphere.create_vbo()

        pos_loc = GL.glGetUniformLocation(self._pegboard_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(self._pegboard_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(self._pegboard_program, "objectScale")
        normal_loc = GL.glGetUniformLocation(self._pegboard_program, "normalMode")

        # A real cylinder/sphere mesh (unlike a flat quad) looks
        # noticeably better smooth-shaded.
        GL.glUniform1i(normal_loc, 1)

        joints: dict = {}  # waypoint_id -> (x, z, width, color)

        for edge, strand in zip(self._edges, self._bundle_strands):
            material = _materials.Generic(strand.color)
            material.set(self._pegboard_program)

            length, (qw, qx, qy, qz) = _strand_mesh.cylinder_placement(
                (edge.node_a.x, edge.node_a.z), (edge.node_b.x, edge.node_b.z))

            GL.glUniform3f(pos_loc, edge.node_a.x, 0.0, edge.node_a.z)
            GL.glUniform4f(rot_loc, qw, qx, qy, qz)
            GL.glUniform3f(scale_loc, strand.width, strand.width, length)
            cylinder_vbo.render()

            for node in (edge.node_a, edge.node_b):
                if node.waypoint_id is not None:
                    joints[node.waypoint_id] = (
                        node.x, node.z, strand.width, strand.color)

        for x, z, width, color in joints.values():
            material = _materials.Generic(color)
            material.set(self._pegboard_program)

            GL.glUniform3f(pos_loc, x, 0.0, z)
            GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
            GL.glUniform3f(scale_loc, width, width, width)
            sphere_vbo.render()

    def _render_objects(self):
        """Render placed peg-board scene objects.

        A read-only top-down render of every anchor in ``self._anchors``
        (see :meth:`load_project`/:meth:`add_anchor`/:meth:`remove_anchor`
        and ``objects.objectspeg.basepeg.BasePeg``), reusing
        the exact same VBOs/materials the 3D editor renders with under the
        schematic2d shader -- mirroring the uniform-setting contract of
        ``objects.objects3d.base3d.Base3D._render_geometry``/``render``.

        Bundle strands (see :meth:`_render_bundle_strands`) and bare-wire
        strands (``gl.canvas_pegboard.layout_graph.build_bare_wire_strands``,
        ``gl.canvas_pegboard.strand_mesh.build_strand_quad``) are drawn
        under this same program/uniform contract, before the anchor loop
        -- strands sit "under" the real 3D meshes visually.

        No object picking/dragging exists yet (Phase 1 is READ-ONLY) --
        that is a later task's job, once the peg-board scene-object model
        supports it.
        """
        if self._pegboard_program is None:
            return

        if not self._anchors and not self._bundle_strands and not self._bare_wire_strands:
            return

        if self.size is None:
            return

        width, height = self.size
        if width == 0 or height == 0:
            return

        GL.glUseProgram(self._pegboard_program)

        projection = self._pegboard_projection_matrix()
        view = np.eye(4, dtype=np.float32)

        proj_loc = GL.glGetUniformLocation(self._pegboard_program, "projection")
        view_loc = GL.glGetUniformLocation(self._pegboard_program, "view")
        flip_y_loc = GL.glGetUniformLocation(self._pegboard_program, "flipY")
        camera_loc = GL.glGetUniformLocation(self._pegboard_program, "cameraPos2D")
        light_color_loc = GL.glGetUniformLocation(self._pegboard_program, "lightColor")
        light_intensity_loc = GL.glGetUniformLocation(self._pegboard_program, "lightIntensity")
        render_mode_loc = GL.glGetUniformLocation(self._pegboard_program, "renderMode")

        # gl.canvas3d.canvas.Canvas always builds its matrices already
        # column-major and uploads with GL_FALSE -- match that convention
        # here too (transpose the row-major array built above ourselves,
        # rather than relying on the transpose flag) instead of mixing
        # conventions across the codebase.
        GL.glUniformMatrix4fv(proj_loc, 1, GL.GL_FALSE, np.ascontiguousarray(projection.T))
        GL.glUniformMatrix4fv(view_loc, 1, GL.GL_FALSE, np.ascontiguousarray(view.T))

        # World coords (Y-up), not screen coords -- matches this canvas's
        # world-unit-direct _setup_projection convention (no flip).
        GL.glUniform1i(flip_y_loc, 0)
        GL.glUniform2f(camera_loc, self.camera.x, self.camera.y)
        GL.glUniform3f(light_color_loc, 1.0, 1.0, 1.0)
        GL.glUniform1f(light_intensity_loc, 1.0)
        GL.glUniform1i(render_mode_loc, 0)  # filled

        # Rebuild the GPU-side bare-wire-strand VBOs if load_project() ran
        # since the last frame -- deferred here because it's the one
        # place a current GL context is guaranteed (see
        # _rebuild_strand_draws()). Bundle strands need no equivalent
        # rebuild step at all -- _render_bundle_strands() reads live node
        # positions directly, every frame, unconditionally.
        if self._strand_draws_dirty:
            self._rebuild_strand_draws()

        # Bundle strands first (thick, filled), then bare-wire strands
        # (thin) -- both drawn before the anchor loop below so the real
        # 3D meshes visually sit "on top of" the flat strands from this
        # top-down view.
        self._render_bundle_strands()
        self._render_strand_draws(self._bare_wire_strand_draws)

        # Per-object uniform locations don't change between anchors within
        # this one program -- fetched once per frame rather than once per
        # anchor.
        pos_loc = GL.glGetUniformLocation(self._pegboard_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(self._pegboard_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(self._pegboard_program, "objectScale")
        normal_loc = GL.glGetUniformLocation(self._pegboard_program, "normalMode")

        for anchor in self._anchors:
            # Selection highlight: reuse the exact same
            # Base3D._selected_material (Config.editor3d.selected_color)
            # the 3D editor already swaps to on selection -- read live via
            # anchor.obj.obj3d.material instead of the anchor's own
            # snapshotted ``material`` field, since that snapshot is only
            # rebuilt on load_project() and would otherwise go stale the
            # moment selection changes from another editor. Only the
            # selected anchor pays this extra hop; every other anchor
            # keeps using its snapshotted material as before.
            if anchor.obj.is_selected:
                material = anchor.obj.obj3d.material
            else:
                material = anchor.material

            material.set(self._pegboard_program)

            quat_w, quat_x, quat_y, quat_z = [
                float(str(v)) for v in anchor.angle.as_quat_numpy.tolist()]

            GL.glUniform3f(pos_loc, anchor.position.x, anchor.position.y, anchor.position.z)
            GL.glUniform4f(rot_loc, quat_w, quat_x, quat_y, quat_z)
            GL.glUniform3f(scale_loc, *anchor.scale.as_float)
            GL.glUniform1i(normal_loc, int(anchor.smooth))

            # Both PooledVBOHandler and NonPooledVBOHandler auto-acquire
            # their VAO for the current GL context inside render() itself
            # -- no explicit acquire() call needed here.
            anchor.vbo.render()

        # Rotation gizmo (if "rotation mode" is active for an anchor) --
        # rendered last so it draws on top of every anchor mesh, under the
        # same already-bound schematic2d program/uniform contract. Built
        # lazily here (needs a current GL context, guaranteed inside
        # paintGL()) rather than at enter_rotation_mode() call time --
        # mirrors the strand-draws dirty-flag pattern above.
        if self._rotation_gizmo_dirty:
            self._rebuild_rotation_gizmo()

        if self._rotation_gizmo is not None and self._rotation_gizmo_anchor is not None:
            self._rotation_gizmo.render(
                self._pegboard_program, self._rotation_gizmo_degrees)

        # Table-drag leader line (if a table overlay is currently being
        # dragged) -- rendered last, same as the rotation gizmo, so it
        # draws on top of everything else.
        if self._table_drag_anchor_pos is not None:
            if self._table_drag_line_dirty or self._table_drag_line_draw is None:
                self._rebuild_table_drag_line()

            if self._table_drag_line_draw is not None:
                self._render_strand_draws([self._table_drag_line_draw])

        GL.glUseProgram(0)

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def _setup_projection(self):
        """Set up the top-down orthographic projection from the camera."""
        if self.size is None:
            return

        width, height = self.size
        if width == 0 or height == 0:
            return

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        world_per_pixel = self.camera.distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self.camera.x - half_width
        right = self.camera.x + half_width
        bottom = self.camera.y - half_height
        top = self.camera.y + half_height

        GL.glOrtho(left, right, bottom, top, -1.0, 1.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
