# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board floating wire table -- Peg Board Editor view object.

Owns a hidden :class:`~ui.pegboard_table.mdi_host.PegboardTableHost`
(a real, DB-backed, virtually-scrolled ``WireTable`` inside an off-screen
``QMdiArea``/``QMdiSubWindow``), captures it to a GL texture, and draws
that texture on this object's own world-space quad -- the same shared
unit-quad VBO/position/scale every other object already renders through
(``_render_geometry``), just with ``shaders.texture`` bound to a captured
Qt widget instead of ``shaders.faces`` lighting a real mesh.

Mouse interaction with the hidden widget only happens once this table is
the SELECTED object (the user's own explicit design call -- "mouse events
over them will not do anything unless it is selected... this locks down
mouse interactions with that table"): an unselected table behaves like
any other pegboard object under the mouse (plain click selects it, drag
would move it -- see ``BasePegboard.drag``), and only once selected does
:meth:`handle_interaction`/:meth:`handle_wheel` start forwarding events
into the hidden ``QMdiSubWindow``, using the exact synthetic-event
dispatch techniques proven in the scratch prototype this whole feature
started as (``scratches/pegboard_spreadsheet_widget/gl_qtable_test.py`` --
see that file for the "why" behind the hover-before-press requirement,
mouse-grab emulation across press/drag/release, etc.).

The anchor-to-table connecting line (see :meth:`render`) is a straight,
base-anchored cylinder -- the exact same ``shapes.cylinder.create_vbo``/
``geometry.angle.Angle.from_points`` construction
``objects_pegboard.wire.Wire`` already uses for a wire segment (position =
the anchor end, angle aligns the cylinder's local +Z to the anchor->table
direction, scale = ``(diameter, diameter, length)``), rendered at a fixed
negative Y (:data:`_LINE_DEPTH_Y`) so it never draws on top of either the
anchor (usually Y=0) or this table's own texture (``pjt_pegboard_table.
TABLE_DEPTH_Y``, elevated). Its angle/scale are cached and only recomputed
when either endpoint actually moves (see :meth:`_update_position`/
:meth:`_update_connector`), not per-frame.
"""

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL
from PySide6 import QtCore, QtGui, QtWidgets

from . import base_pegboard as _base_pegboard
from ...shapes import rectangle as _rectangle
from ...shapes import cylinder as _cylinder
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...ui.pegboard_table import mdi_host as _mdi_host
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import pegboard_table as _pegboard_table
    from ...database.project_db import pjt_pegboard_table as _pjt_pegboard_table
    from ...gl import shaders as _shaders


# Fixed depth for the anchor-to-table connecting line -- always below both
# a normal anchor's own peg-board Y (0.0 by default) and this table's own
# elevated Y (``pjt_pegboard_table.TABLE_DEPTH_Y``), so the line never
# visibly draws on top of either one regardless of where they actually sit.
_LINE_DEPTH_Y = -1.0

# Diameter of the connecting-line cylinder, in world units -- the shared
# cylinder mesh's own default radius is 0.5 (see shapes.cylinder.create),
# so scale.x/scale.y directly produce this diameter.
_LINE_DIAMETER = 0.25

# Selection-border depth -- slightly ABOVE this table's own elevated Y
# (see pjt_pegboard_table.TABLE_DEPTH_Y) so the border always draws on
# top of the table's own texture quad rather than under it.
_BORDER_DEPTH_OFFSET = 0.5

# The table's own quad has its top corners come out rounded on their
# own, for free, via WA_TranslucentBackground letting the native
# title-bar chrome's own real rounding show through as transparency
# (see mdi_host.py). Its bottom corners are square, but the captured
# native chrome leaves a faint, partially-transparent curved line right
# at those two otherwise-square corners (confirmed 2026-09-16, Kevin:
# "the bottom corners are rendered as square but they have a gray
# rounded line") -- a genuine rounded clip (cornerRadiusPx, same
# mechanism as the top corners and the selection border) removes it
# cleanly. A plain square discard was tried first and rejected (Kevin,
# 2026-09-16: "that's not a rounded corner... you are taking a chunk of
# the corner out, not rounding it") -- a real curve, not a notch.
_BOTTOM_CORNER_RADIUS_PX = 4.0

# Selection border -- WORLD units (mm), not screen pixels, so it scales
# with the table itself as the user zooms (a previous, screen-pixel-
# fixed version stayed a constant 2px on screen regardless of zoom,
# per Kevin 2026-09-16 not the wanted behavior). Drawn as a genuine
# ring (ringThicknessPx) immediately outside the table's own quad --
# see _render_selection_border's own docstring. 1.0 looked "way too
# thick" (Kevin, 2026-09-16); 0.5 is half that.
_BORDER_THICKNESS_MM = 0.5

# Resize HIT-TEST margin, deliberately NOT the same as the visible
# border's own _BORDER_THICKNESS_MM -- _resize_zone_at's corner zones
# are the overlap of the x- and z-margin bands, so sizing the hit area
# to match a thin cosmetic ring made every corner a ~0.5x0.5mm target
# (Kevin, 2026-09-16: "it's only like a 2 pixel hit area... very
# touchy"). A separate, generously wider margin here keeps the VISUAL
# ring thin while giving the grab area the wider-than-its-own-outline
# sizing every resize handle needs -- ordinary window-manager resize
# borders work the same way (invisible, wider than any drawn line).
_RESIZE_HIT_MARGIN_MM = 3.0

# (top-left, top-right, bottom-right, bottom-left) -- rounded on all 4
# corners (Kevin, 2026-09-16: "make the green border have rounded
# bottom corners as well"). 1.5 looked too loose; 0.75 is half that
# (Kevin, 2026-09-16: "tighten up the corner radius... 1/2 of what it
# currently is set to").
_BORDER_CORNER_RADIUS_MM = (1.15, 1.15, 1.15, 1.15)

# Solid, fully opaque green, uploaded once as a 1x1 GL texture and
# reused every frame -- see _render_selection_border for why the
# border is drawn through shaders.texture (reusing its existing
# quadSizePx/cornerRadiusPx rounded-rect clip) rather than shaders.
# faces.
_BORDER_RGBA = bytes([0, 255, 0, 255])

# Never resize a table smaller than this, in world mm, on either axis
# (Kevin, 2026-09-16: "we need to make the thing resizable... we have
# the green border that can be used as the resize border").
_MIN_TABLE_SIZE_MM = 20.0

# Cursor shape for each (x_edge, z_edge) resize zone -- see
# _resize_zone_at's own docstring for what these pairs mean. Diagonal
# choice (FDiag "\\" vs BDiag "/") follows canvas.py's own documented
# camera convention (gl.canvas_pegboard.canvas.Canvas._set_view: "side
# stays (1,0,0)", "up becomes (0,0,-1)") -- world -X is screen-left,
# world -Z is screen-up, so (min, min) and (max, max) sit at the
# screen's top-left/bottom-right (a "\\" diagonal) and (max, min)/
# (min, max) sit at top-right/bottom-left (a "/" diagonal).
_RESIZE_CURSOR_FOR_ZONE = {
    ('min', None): QtCore.Qt.CursorShape.SizeHorCursor,
    ('max', None): QtCore.Qt.CursorShape.SizeHorCursor,
    (None, 'min'): QtCore.Qt.CursorShape.SizeVerCursor,
    (None, 'max'): QtCore.Qt.CursorShape.SizeVerCursor,
    ('min', 'min'): QtCore.Qt.CursorShape.SizeFDiagCursor,
    ('max', 'max'): QtCore.Qt.CursorShape.SizeFDiagCursor,
    ('max', 'min'): QtCore.Qt.CursorShape.SizeBDiagCursor,
    ('min', 'max'): QtCore.Qt.CursorShape.SizeBDiagCursor,
}


class _TableInteractionHandler:
    """Real (if inert) handler object for :attr:`PegboardTable.
    _active_handler` while a mouse interaction is being forwarded into
    the hidden widget.

    Every other handler in this codebase (``drag_handlers.editor_pegboard.
    generic.Generic``, ``add_handlers.editor_pegboard.wire.Wire``,
    ``rotation_handlers.rotation_rings.RotationRings``, ...) is a real
    object stored on ``_active_handler`` -- ``BaseVar._delete()``
    unconditionally calls ``self._active_handler.delete()`` during
    teardown if it's not ``None``. ``PegboardTable`` does all of its own
    dispatch/rendering directly in :meth:`PegboardTable.handle_interaction`/
    :meth:`PegboardTable.handle_wheel` rather than delegating to a
    separate handler class, so this exists only to satisfy that
    interface -- a bare ``True`` sentinel (what this replaced) has no
    ``delete()`` and would raise ``AttributeError`` the moment the table
    is ever deleted while a drag/press is still armed.

    ``render()`` is the same story, just for a different call site:
    ``BasePegboard.render_handler`` (called once per frame by the
    shared render loop's own deferred pass for whichever object is
    currently selected) unconditionally calls
    ``self._active_handler.render(shaders)`` whenever ``_active_handler``
    is armed -- since :meth:`PegboardTable.set_selected` arms this
    handler for the WHOLE selected duration (not just a drag), that
    fires on every single frame the table is selected, not just while a
    press/drag is in progress. A no-op here (this handler has nothing
    of its own to draw -- the table's own ``render()`` already handles
    everything) is what that call site needs; confirmed 2026-09-16 as
    an ``AttributeError`` crash otherwise.
    """

    @_check_types.do
    def delete(self) -> None:
        pass

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        pass


# Stateless -- one shared instance is reused everywhere PegboardTable
# arms its own _active_handler, rather than allocating a fresh one per
# press/double-click.
_TABLE_HANDLER = _TableInteractionHandler()


class PegboardTable(_base_pegboard.BasePegboard):
    """Peg Board Editor representation of a floating wire table."""

    db_obj: "_pjt_pegboard_table.PJTPegboardTable"

    @_check_types.do
    def __init__(self, parent: "_pegboard_table.PegboardTable",
                 db_obj: "_pjt_pegboard_table.PJTPegboardTable"):
        """Initialise the :class:`PegboardTable` instance.

        :param parent: Parent object.
        :type parent: :class:`_pegboard_table.PegboardTable`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        width, height = db_obj.size
        anchor = db_obj.anchor

        with parent.mainframe.editor_pegboard.context:
            vbo = _rectangle.create_vbo_based()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=_angle.Angle(),
                position=db_obj.position_pegboard,
                scale=_point.Point(width, 1.0, height),
                material=_materials.Plastic(_color.Color(255, 255, 255)),
            )

            self._anchor = anchor
            self._anchor_position = anchor.position_pegboard if anchor is not None else None

            # Locally cached mirror of the anchor's own visibility --
            # deliberately never written back onto this table's own
            # is_visible_pegboard/is_visible (see module docstring on
            # PegboardTable and _on_anchor_visibility_changed's own
            # docstring): this table stays independently show/hide-able
            # by the user (closing the hosted sub-window), and render()
            # additionally skips drawing while the anchor itself is
            # hidden, without the two states ever being conflated.
            self._anchor_is_visible = anchor.is_visible_pegboard if anchor is not None else True
            if anchor is not None:
                anchor.bind(self._on_anchor_visibility_changed, 'is_visible_pegboard')

            self._host = _mdi_host.PegboardTableHost(
                parent.mainframe, self._table_title(), db_obj)
            self._texture_id = GL.glGenTextures(1)
            self._texture_px_size = (1, 1)

            # Connecting-line cylinder -- shared/cached mesh, but this
            # object's own material/angle/scale/position, built once and
            # reused unchanged on every render() call (see module
            # docstring) until an endpoint actually moves.
            self._connector_vbo = _cylinder.create_vbo()
            self._connector_material = _materials.Plastic(_color.Color(0, 0, 0))
            self._connector_position: _point.Point | None = None
            self._connector_angle: _angle.Angle | None = None
            self._connector_scale: _point.Point | None = None

            if self._anchor_position is not None:
                self._anchor_position.bind(self._update_connector)

            self._recompute_connector()

            # Selection border -- see _render_selection_border. Drawn
            # as a solid-green quad through shaders.texture (reusing
            # its existing rounded-rect clip) rather than a faces
            # material, so it gets the exact same corner rounding as
            # the table's own quad for free; a 1x1 opaque-green texture
            # uploaded once here is all that takes.
            self._border_texture_id = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._border_texture_id)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 1, 1, 0,
                GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, _BORDER_RGBA)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
            self._border_angle = _angle.Angle()

        self._host.cursor_changed.connect(self._on_cursor_changed)
        self._host.close_requested.connect(self._on_close_requested)

        # Same "hover reaches the target before press" and "grab-
        # emulation across press/drag/release" state the scratch
        # prototype's own QTableTextureCanvas tracked -- see that
        # file's module docstring for why both are needed.
        self._hover_target: QtWidgets.QWidget | None = None
        self._press_target: QtWidgets.QWidget | None = None
        self._press_local: QtCore.QPoint | None = None

        # Resize-via-green-border state -- see _resize_zone_at/
        # _apply_resize. _resize_zone is the (x_edge, z_edge) pair an
        # in-progress resize drag started on; the _resize_fixed_*
        # values are the OPPOSITE (unmoving) world-space edge(s),
        # frozen at press time so every MOVE during the drag measures
        # from the same anchor rather than compounding off the
        # previous frame's already-resized footprint. _resize_cursor_
        # active tracks whether this table currently owns the canvas's
        # cursor override, so hovering off the border zone knows to
        # release it rather than leaving a stale resize cursor behind.
        self._resize_zone: tuple[str | None, str | None] | None = None
        self._resize_fixed_x: float | None = None
        self._resize_fixed_z: float | None = None
        self._resize_cursor_active = False

        self._regrab_texture()

    @_check_types.do
    def _table_title(self) -> str:
        """Title bar text for the hosted sub-window -- the owning
        anchor's own :attr:`name` (the same common API point every
        anchor type that can own a table exposes, see
        ``pjt_pegboard_table.PJTPegboardTable.anchor``), or a generic
        fallback if no anchor could be found (should not normally
        happen for a live table row).
        """
        if self._anchor is not None:
            return self._anchor.name

        return 'Wire Table'

    @_check_types.do
    def refresh_wires(self) -> None:
        """Requery the hosted ``WireTable``'s row set -- called by
        ``base_pegboard.notify_table_wires_changed`` after a wire's
        connection to this table's own anchor changes.

        ``WireTable.refresh_wire_scope()`` (not the plain ``Refresh()``)
        does the actual requery -- it rebuilds ``_effective_query`` from
        the anchor's CURRENT wire ids, since those are baked into the
        query text itself (see its own docstring); a plain ``Refresh()``
        would just re-render the same, now-stale id list. Also re-grabs
        the GL texture right away, since nothing else would until the
        next mouse interaction with this table.
        """
        self._host.table.refresh_wire_scope()
        self._regrab_texture()

    # ------------------------------------------------------------------
    # Anchor-to-table connecting line
    # ------------------------------------------------------------------

    @_check_types.do
    def _recompute_connector(self) -> None:
        """(Re)compute the cached position/angle/scale for the
        connecting-line cylinder from the anchor's and this table's own
        current X/Z -- called once at construction, and again any time
        either endpoint moves (see :meth:`_update_position`/
        :meth:`_update_connector`). Both endpoints are pinned to
        :data:`_LINE_DEPTH_Y` for this computation only -- the real
        ``Point`` instances backing the anchor's and this table's own
        position are never touched.
        """
        if self._anchor_position is None:
            return

        # self._position.x is the table's LEFT edge, not its center --
        # the rendered quad is base-anchored on X (see _table_screen_
        # rect's own docstring); self._position.z IS already centered.
        # Using position.x directly here landed the connecting line on
        # the table's left edge instead of its center -- confirmed
        # 2026-09-16.
        table_center_x = self._position.x + (self._scale.x / 2.0)

        p1 = _point.Point(self._anchor_position.x, _LINE_DEPTH_Y, self._anchor_position.z)
        p2 = _point.Point(table_center_x, _LINE_DEPTH_Y, self._position.z)

        length = float(np.linalg.norm(p2.as_numpy - p1.as_numpy))

        self._connector_position = p1
        self._connector_angle = _angle.Angle.from_points(p1, p2)
        self._connector_scale = _point.Point(_LINE_DIAMETER, _LINE_DIAMETER, length)

    @_check_types.do
    def _update_connector(self, _position: _point.Point) -> None:
        """Bound to the owning anchor's own live ``position_pegboard`` --
        recompute the connecting line whenever the anchor itself moves.
        See :meth:`_update_position` for the table-side half of the same
        recompute.
        """
        self._recompute_connector()
        self.pegboard.Refresh()

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """Extends the inherited position-change handling (OBB/AABB
        translation, repaint -- see ``BaseVar._update_position``) to also
        keep the connecting line current whenever this table itself
        moves (dragged by the user, or nudged by :meth:`_regrab_texture`
        after an in-place MDI sub-window drag).
        """
        super()._update_position(position)
        self._recompute_connector()

    @_check_types.do
    def _on_anchor_visibility_changed(self, *_args, **_kwargs) -> None:
        """Bound to the owning anchor's own ``is_visible_pegboard``
        column -- mirrors it into :attr:`_anchor_is_visible` (re-read
        fresh from the anchor rather than trusting whatever *_args*
        carries, same defensive style as ``BasePegboard.
        __is_visible_callback``) so :meth:`render` can skip drawing
        while the anchor itself is hidden. Never writes back onto this
        table's own ``is_visible_pegboard``/``is_visible`` -- see
        the constructor's own comment on why those stay independent.
        """
        self._anchor_is_visible = self._anchor.is_visible_pegboard
        self.pegboard.Refresh()

    # ------------------------------------------------------------------
    # Texture capture/upload
    # ------------------------------------------------------------------

    @_check_types.do
    def _regrab_texture(self) -> None:
        """Capture the hidden widget's current appearance and upload it
        as this object's live GL texture -- same technique as the
        scratch prototype's own ``_regrab_texture``, just writing world-
        space position deltas straight to the real, bindable
        ``self._position`` (a live ``Point`` shared with the DB layer)
        instead of a canvas-local ``anchor_x``/``anchor_z`` pair.

        The actual texture upload is wrapped in ``self.pegboard.context``
        (``gl.context.GLContext`` -- re-entrant, and re-verifies/re-
        establishes current-ness on every acquire even if some OTHER
        widget's own repaint stole it since) rather than assuming the
        peg-board canvas's own GL context is already current. It isn't,
        always: this method is also called from
        ``base_pegboard.notify_table_wires_changed`` -> ``refresh_wires``,
        reachable from wherever a wire's connection to an anchor changes
        -- e.g. from the 3D editor's own interaction dispatch, which
        leaves the 3D canvas's context current, not this one's. Confirmed
        2026-09-16: an unguarded ``glBindTexture`` there raised
        GL_INVALID_OPERATION.
        """
        delta = self._host.sub_window_moved()
        if delta.x() or delta.y():
            # delta is in the HOST's own logical pixels (see
            # PegboardTableHost.sub_window_moved) -- world units here are
            # millimeters, so it has to come back down through the same
            # devicePixelRatio/PIXELS_PER_MM scale the width/height sync
            # below uses, not be added to world-space self._position
            # directly. Confirmed 2026-09-16: applying the raw pixel
            # delta as though it were already mm inflated every drag/
            # resize step by PIXELS_PER_MM (6x), making the table "jump
            # all over the place" on a title-bar drag and making an
            # edge-resize (which also moves .pos() when dragging the
            # top/left edge) look broken the same way.
            host_dpr = self._host.devicePixelRatio()
            with self._position:
                self._position.x += (float(delta.x()) / host_dpr) / _mdi_host.PIXELS_PER_MM
                self._position.z += (float(delta.y()) / host_dpr) / _mdi_host.PIXELS_PER_MM

            # `with point:` batches the two component writes above but,
            # per Point/CallbackMixin's own docstring, does NOT fire
            # bound callbacks on __exit__ -- "the caller is responsible
            # for triggering the update itself after the block". Since
            # this table owns self._position outright (unlike the
            # anchor's point, which is a genuinely SHARED point this
            # object only reacts to via .bind()), the established
            # pattern elsewhere for a self-owned position (see e.g.
            # objects_pegboard.wire_marker's own `with self._position:`
            # users, which call _compute_obb/_compute_aabb directly
            # afterward rather than relying on a callback) is to update
            # this object's own derived state explicitly -- calling our
            # own _update_position override does that (OBB/AABB
            # translation via the inherited half, the connecting line
            # via _recompute_connector). Without this, neither ever
            # updated on a table drag: the OBB stayed at the pre-drag
            # position (confirmed 2026-09-16 as "can't select the table
            # again" after moving it -- the click was hit-testing a
            # stale box) and the connecting line never moved either.
            self._update_position(self._position)

            self._host.reset_sub_window_position()

        rgba, width, height = self._host.grab_rgba()

        with self.pegboard.context:
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
            GL.glTexImage2D(
                GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0,
                GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, rgba)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self._texture_px_size = (width, height)

        # The hosted widget's own pixel size is the real source of
        # truth for this table's world-space footprint (a native
        # QMdiSubWindow resize changes ITS size directly, not
        # self._scale) -- keep them in sync, and persist to the DB the
        # same way a drag persists position via the bound Point.
        #
        # Divides by the HOST's own devicePixelRatio (expected to be
        # 1.0 -- it's WA_DontShowOnScreen, never associated with a real
        # screen), NOT the on-screen canvas's -- those are two different
        # widgets with potentially two different ratios. World units in
        # this codebase are millimeters, not logical pixels, so the
        # result is also divided by mdi_host.PIXELS_PER_MM (see that
        # constant's own comment) -- anchored to the HOST's own logical
        # pixels specifically, same as _screen_to_panel_local's inverse
        # conversion.
        host_dpr = self._host.devicePixelRatio()
        world_w = (width / host_dpr) / _mdi_host.PIXELS_PER_MM
        world_h = (height / host_dpr) / _mdi_host.PIXELS_PER_MM
        if (self._scale.x, self._scale.z) != (world_w, world_h):
            with self._scale:
                self._scale.x = world_w
                self._scale.z = world_h

            self.db_obj.size = (world_w, world_h)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Draw the captured widget texture on this object's own quad,
        then the anchor-to-table connecting line.

        Reuses :meth:`_render_geometry` exactly as the generic
        ``BaseVar.render`` does for ``shaders.faces`` -- it already
        reads ``self._vbo``/``self._position``/``self._angle``/
        ``self._scale`` and sets the program's position/rotation/scale
        uniforms accordingly, so the only thing specific to a textured
        quad is binding the actual GL texture around that same call.

        Also skips drawing while the owning anchor itself is hidden
        (:attr:`_anchor_is_visible`, kept current by
        :meth:`_on_anchor_visibility_changed`) -- this table's own
        ``is_visible``/``is_visible_pegboard`` is never touched by that,
        so it comes right back once the anchor is shown again.
        """
        if not self.is_visible:
            return

        if not self._anchor_is_visible:
            return

        if self._vbo is None:
            return

        # Drawn BEFORE the table's own quad, not after -- see
        # _render_selection_border's own docstring for why: it's a
        # solid-green rounded quad slightly LARGER than the table on
        # every side, and the table's own opaque, GL_ALWAYS-forced draw
        # right below completely overwrites its center, leaving only a
        # ring of it visible -- no separate ring/outline math needed.
        if self.is_selected:
            self._render_selection_border(shaders)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)

        # This table must always render on top of ordinary scene
        # geometry -- TABLE_DEPTH_Y's elevated Y only wins the normal
        # GL_LESS depth test against whatever renders AFTER this call in
        # the same frame; anything drawn BEFORE it (this frame's
        # per-object draw order is whatever _draw_scene's own object
        # list happens to be, not depth-sorted) already occupies the
        # color+depth buffers, and GL_LESS alone can't retroactively
        # win against that. Confirmed 2026-09-16: the table still
        # rendered under ordinary objects even while unselected (so not
        # the earlier is_opaque/deferred-translucent-pass issue).
        # GL_ALWAYS for just this one draw guarantees it wins regardless
        # of where it fell in this frame's draw order, while still
        # writing its own (correctly elevated) depth -- restored to
        # GL_LESS immediately after, so the connecting line/selection
        # border right below (and anything drawn later this frame) are
        # still tested normally against that now-written depth.
        GL.glDepthFunc(GL.GL_ALWAYS)
        with shaders.texture:
            # Square top corners (the native chrome's own real rounding
            # already shows through there via WA_TranslucentBackground,
            # so 0 here just leaves that alone), rounded bottom corners
            # -- explicitly set (not left unset) since shaders.texture
            # is the SAME GL program _render_selection_border uses, and
            # uniform values persist across draw calls until set again.
            shaders.texture.quad_size_px = self._texture_px_size
            shaders.texture.corner_radius_px = (
                0.0, 0.0, _BOTTOM_CORNER_RADIUS_PX, _BOTTOM_CORNER_RADIUS_PX)
            shaders.texture.ring_thickness_px = 0.0
            shaders.texture.bottom_corner_trim_px = 0.0
            self._render_geometry(shaders.texture)
        GL.glDepthFunc(GL.GL_LESS)

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        self._render_connector(shaders)

    @_check_types.do
    def _render_connector(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the connecting line -- same "temporarily point this
        object's own position/angle/scale/material/vbo at the thing
        actually being drawn, delegate to the inherited faces render,
        then restore" technique ``objects_pegboard.wire.Wire.render``
        already uses per-segment.

        No-op when there's no anchor to connect to (e.g. ``anchor``
        couldn't be resolved -- see ``pjt_pegboard_table.
        PJTPegboardTable.anchor``).
        """
        if self._anchor_position is None or self._connector_scale is None:
            return

        real_vbo, real_position, real_angle, real_scale, real_material = (
            self._vbo, self._position, self._angle, self._scale, self._material)

        self._vbo = self._connector_vbo
        self._position = self._connector_position
        self._angle = self._connector_angle
        self._scale = self._connector_scale
        self._material = self._connector_material

        # BaseVar.material is a PROPERTY that returns self._selected_
        # material whenever self._is_selected is True, ignoring
        # self._material entirely -- so while this whole table is
        # selected, the swap above had no effect and super().render()
        # picked up the table's own translucent "selected" highlight
        # material instead of the connector's real opaque black one.
        # That alpha-blended draw is what put the line on TOP of the
        # table's own opaque quad regardless of their actual Y depth,
        # and (GL blend state not otherwise reset before whatever
        # renders next) is also the likely cause of other objects
        # appearing to render on top of the table -- confirmed
        # 2026-09-16. Temporarily clearing is_selected for this one
        # nested render call routes material back to self._material
        # (the connector's own), same as it would for an unselected
        # table.
        real_is_selected = self._is_selected
        self._is_selected = False

        super().render(shaders)

        self._is_selected = real_is_selected
        self._vbo, self._position, self._angle, self._scale, self._material = (
            real_vbo, real_position, real_angle, real_scale, real_material)

    @_check_types.do
    def _render_selection_border(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw a fully opaque green rounded-rect RING selection
        indicator immediately outside this table's own quad, through
        ``shaders.texture`` against a solid-green 1x1 GL texture
        (:attr:`_border_texture_id`) instead of ``shaders.faces``,
        reusing that shader's existing rounded-rect clip
        (``fragment.frag``'s own ``roundedRectDist``/``ringThicknessPx``)
        to round this quad's corners the exact same way the table's own
        quad is rounded.

        A genuine ring (``ringThicknessPx``), NOT a filled quad relying
        on the table's own opaque draw right after this one to "punch a
        hole" through its center -- that was the first version of this,
        and it broke as soon as the table's own quad had ANY gap in its
        own coverage (a since-reverted top/left margin crop, back when
        the table's own quad was still being cropped/rounded to work
        around what turned out to be a mispositioned capture rect, not
        real native chrome -- see the module-level comment above
        _BORDER_THICKNESS_MM). A self-contained ring has no such
        dependency on what the table's own quad does or doesn't cover.

        Explicit rather than relying on ``BaseVar``'s generic "selected
        material" tint, which only ever affected the connecting line by
        accident (see :meth:`_render_connector`'s own comment) -- the
        table's own quad is drawn with ``shaders.texture`` and never
        consults ``self.material`` at all.

        World-space thickness (``_BORDER_THICKNESS_MM``), not a fixed
        screen-pixel width -- so it scales with the table itself as the
        user zooms, same as everything else drawn in world space,
        rather than staying a constant on-screen width (Kevin,
        2026-09-16).
        """
        thickness = _BORDER_THICKNESS_MM

        # Outer boundary sits exactly `thickness` beyond the table's
        # own true footprint; ringThicknessPx then keeps only the
        # `thickness`-wide band just inside that boundary, which lands
        # exactly on the table's own edge.
        position = _point.Point(
            self._position.x - thickness,
            self._position.y + _BORDER_DEPTH_OFFSET,
            self._position.z)
        scale = _point.Point(
            self._scale.x + (2.0 * thickness), 1.0,
            self._scale.z + (2.0 * thickness))

        angle = _rectangle.create_vbo_based().render_angle(self._border_angle)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._border_texture_id)

        GL.glDepthFunc(GL.GL_ALWAYS)
        with shaders.texture:
            shaders.texture.quad_size_px = (scale.x, scale.z)
            shaders.texture.corner_radius_px = _BORDER_CORNER_RADIUS_MM
            shaders.texture.ring_thickness_px = thickness
            # Explicitly zeroed -- shaders.texture is the SAME GL
            # program the table's own draw uses, and uniform values
            # persist across draw calls (this one runs first each
            # frame, so without this it would inherit whatever the
            # table's own bottom_corner_trim_px was left at from the
            # PREVIOUS frame).
            shaders.texture.bottom_corner_trim_px = 0.0
            _rectangle.create_vbo_based().render(shaders.texture, position, angle, scale, None)
        GL.glDepthFunc(GL.GL_LESS)

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    # ------------------------------------------------------------------
    # Interaction -- only while this table is the selected object (see
    # module docstring).
    # ------------------------------------------------------------------

    @_check_types.do
    def _table_screen_rect(self) -> tuple[float, float, float, float]:
        """This table's own on-screen pixel rect, from its live
        world-space position/scale.

        The rendered quad (``shapes.rectangle.create_vbo_based``, see
        ``__init__``) is base-anchored on local X (``[0, 1]``) and only
        centered on local Z (``[-0.5, 0.5]``) -- ``vertex.vert`` computes
        ``worldPosition = (in_vertexLocal * objectScale) + objectPosition``,
        so the table's actual world-space X range is ``[self._position.x,
        self._position.x + self._scale.x]``, NOT centered on
        ``self._position.x`` the way Z is on ``self._position.z``. Using a
        symmetric ``position.x +/- half_w`` range here (matching Z) landed
        this rect consistently offset from the real rendered/hit-tested
        quad -- confirmed 2026-09-16 as "hover highlight is columns over,
        same row" (Z, actually centered, tracked correctly; X did not).

        In LOGICAL canvas pixels, matching what ``mouse_handler_base.
        _qt_pos`` hands ``handle_interaction`` as ``current_pos``/
        ``last_pos`` (``QMouseEvent.position()``, never DPR-converted) --
        ``camera.world_to_screen`` itself works in DEVICE pixels
        (``canvas.size`` is set from ``resizeGL``'s own width/height,
        which Qt already reports in device pixels -- confirmed via the
        ``GL.glViewport(0, 0, width, height)`` call right next to it in
        ``canvas_pegboard/canvas.py``), so its result is divided back
        down to logical pixels here for a fair comparison against
        ``current_pos``.

        Also: ``Point``'s 2-argument screen-space convention is ``(x,
        y)`` -- ``camera.world_to_screen`` returns ``Point(screen_x,
        screen_y)``, i.e. ``.y``, NOT ``.z`` (``.z`` is what a WORLD-
        space ``Point(x, y=0.0, z)`` uses for its second axis -- easy to
        mix up since both conventions appear side by side in this same
        method).

        :returns: ``(left, top, right, bottom)`` in canvas-local,
            logical pixels.
        :rtype: tuple[float, float, float, float]
        """
        half_h = self._scale.z / 2.0

        camera = self.pegboard.camera
        dpr = camera.canvas.devicePixelRatio()

        corner1 = camera.world_to_screen(
            _point.Point(self._position.x, 0.0, self._position.z - half_h))
        corner2 = camera.world_to_screen(
            _point.Point(self._position.x + self._scale.x, 0.0, self._position.z + half_h))

        x1, y1 = corner1.x / dpr, corner1.y / dpr
        x2, y2 = corner2.x / dpr, corner2.y / dpr

        return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    @_check_types.do
    def _point_in_table_rect(self, screen_pos: _point.Point) -> bool:
        left, top, right, bottom = self._table_screen_rect()
        return left <= screen_pos.x <= right and top <= screen_pos.y <= bottom

    @_check_types.do
    def _screen_to_world(self, screen_pos: _point.Point) -> _point.Point:
        """Canvas screen pixels (logical) -> world -- the device-pixel
        conversion :meth:`_screen_to_panel_local` also does, factored
        out since :meth:`_resize_zone_at`/:meth:`_apply_resize` need
        the plain world position, not a panel-local one.
        """
        camera = self.pegboard.camera
        dpr = camera.canvas.devicePixelRatio()
        device_screen_pos = _point.Point(screen_pos.x * dpr, screen_pos.y * dpr)
        return camera.screen_to_world(device_screen_pos)

    @_check_types.do
    def _resize_zone_at(self, screen_pos: _point.Point) -> tuple[str | None, str | None] | None:
        """Classify *screen_pos* against a resize-grab zone around the
        table -- its footprint expanded by ``_RESIZE_HIT_MARGIN_MM`` on
        every side, deliberately wider than the green border's own,
        thinner, purely cosmetic ``_BORDER_THICKNESS_MM`` (see that
        constant's own comment, and :meth:`_render_selection_border`
        for the visual ring itself). Done entirely in WORLD space
        rather than screen space: the
        top-down camera's own screen-Y-vs-world-Z relationship is a
        documented but easy-to-get-backwards sign flip (see
        ``canvas_pegboard.canvas.Canvas._set_view``'s own comment), and
        comparing world coordinates directly against the table's own
        world-space footprint sidesteps needing to resolve it at all
        for the hit-test/resize math (only the cursor SHAPE choice, in
        :data:`_RESIZE_CURSOR_FOR_ZONE`, still needs it, and that's
        looked up from the result this returns, not recomputed here).

        :returns: ``None`` if *screen_pos* is inside the table's own
            interior or entirely outside the border ring; otherwise an
            ``(x_edge, z_edge)`` pair, each ``'min'``/``'max'``/``None``,
            naming which world-space edge(s) of the table's footprint
            the point is beyond -- ``x_edge`` is ``'min'`` beyond
            ``self._position.x`` (the left edge) and ``'max'`` beyond
            ``self._position.x + self._scale.x`` (the right edge);
            ``z_edge`` likewise for the table's centered Z extent. Both
            non-``None`` means a corner zone.
        """
        world_pos = self._screen_to_world(screen_pos)

        thickness = _RESIZE_HIT_MARGIN_MM
        min_x = self._position.x
        max_x = self._position.x + self._scale.x
        min_z = self._position.z - (self._scale.z / 2.0)
        max_z = self._position.z + (self._scale.z / 2.0)

        if not (min_x - thickness <= world_pos.x <= max_x + thickness and
                min_z - thickness <= world_pos.z <= max_z + thickness):
            return None

        if min_x <= world_pos.x <= max_x and min_z <= world_pos.z <= max_z:
            return None

        x_edge = None
        if world_pos.x < min_x:
            x_edge = 'min'
        elif world_pos.x > max_x:
            x_edge = 'max'

        z_edge = None
        if world_pos.z < min_z:
            z_edge = 'min'
        elif world_pos.z > max_z:
            z_edge = 'max'

        if x_edge is None and z_edge is None:
            return None

        return (x_edge, z_edge)

    @_check_types.do
    def _set_resize_cursor(self, zone: tuple[str | None, str | None] | None) -> None:
        """Show the resize cursor for *zone* (see
        :data:`_RESIZE_CURSOR_FOR_ZONE`), or release this table's own
        cursor override if *zone* is ``None`` -- tracked via
        :attr:`_resize_cursor_active` so a plain ``unsetCursor()`` isn't
        called on every hover move regardless of whether this table
        actually set one (which would fight with the hidden widget's
        own ``cursor_changed``-driven overrides, see
        :meth:`_on_cursor_changed`).
        """
        canvas = self.pegboard.camera.canvas

        if zone is None:
            if self._resize_cursor_active:
                canvas.unsetCursor()
                self._resize_cursor_active = False
            return

        shape = _RESIZE_CURSOR_FOR_ZONE.get(zone)
        if shape is None:
            return

        canvas.setCursor(QtGui.QCursor(shape))
        self._resize_cursor_active = True

    @_check_types.do
    def _start_resize(self, zone: tuple[str | None, str | None]) -> None:
        """Begin a resize drag in *zone* -- freezes the OPPOSITE
        (unmoving) world-space edge(s) into :attr:`_resize_fixed_x`/
        :attr:`_resize_fixed_z` so every subsequent :meth:`_apply_resize`
        call measures from the same anchor for the whole drag, rather
        than compounding off whatever the table's footprint happened to
        be one frame ago.
        """
        x_edge, z_edge = zone
        self._resize_zone = zone

        if x_edge == 'min':
            self._resize_fixed_x = self._position.x + self._scale.x
        elif x_edge == 'max':
            self._resize_fixed_x = self._position.x
        else:
            self._resize_fixed_x = None

        if z_edge == 'min':
            self._resize_fixed_z = self._position.z + (self._scale.z / 2.0)
        elif z_edge == 'max':
            self._resize_fixed_z = self._position.z - (self._scale.z / 2.0)
        else:
            self._resize_fixed_z = None

    @_check_types.do
    def _apply_resize(self, screen_pos: _point.Point) -> None:
        """Resize the table to track *screen_pos*, given an in-progress
        drag started by :meth:`_start_resize` -- computes the new
        world-space footprint (clamped to :data:`_MIN_TABLE_SIZE_MM` on
        each axis actually being resized), applies it to this object's
        own ``self._position``/``self._scale`` directly (mirroring the
        anchor-edge math, not delta-accumulation, so it can't drift),
        resizes the REAL hidden ``QMdiSubWindow`` to match, and re-grabs
        -- which, via its own existing width/height sync (see
        :meth:`_regrab_texture`), reconciles ``self._scale`` against
        whatever the captured widget's own pixel size actually came out
        to (minor int-truncation aside), the same source-of-truth
        pattern every other size change here already follows.
        """
        world_pos = self._screen_to_world(screen_pos)
        x_edge, z_edge = self._resize_zone

        if x_edge == 'min':
            new_width = max(_MIN_TABLE_SIZE_MM, self._resize_fixed_x - world_pos.x)
            new_x = self._resize_fixed_x - new_width
        elif x_edge == 'max':
            new_width = max(_MIN_TABLE_SIZE_MM, world_pos.x - self._resize_fixed_x)
            new_x = self._resize_fixed_x
        else:
            new_width = self._scale.x
            new_x = self._position.x

        if z_edge == 'min':
            new_height = max(_MIN_TABLE_SIZE_MM, self._resize_fixed_z - world_pos.z)
            new_center_z = self._resize_fixed_z - (new_height / 2.0)
        elif z_edge == 'max':
            new_height = max(_MIN_TABLE_SIZE_MM, world_pos.z - self._resize_fixed_z)
            new_center_z = self._resize_fixed_z + (new_height / 2.0)
        else:
            new_height = self._scale.z
            new_center_z = self._position.z

        with self._position:
            self._position.x = new_x
            self._position.z = new_center_z
        self._update_position(self._position)

        width_px = max(1, int(new_width * _mdi_host.PIXELS_PER_MM))
        height_px = max(1, int(new_height * _mdi_host.PIXELS_PER_MM))
        self._host.sub_window.resize(width_px, height_px)

        self._regrab_texture()

    @_check_types.do
    def _screen_to_panel_local(self, screen_pos: _point.Point) -> QtCore.QPointF:
        """Inverse of the quad placement in :meth:`render` -- canvas
        screen pixels -> world -> the hidden panel's own local pixel
        space (top-left-origin, matching a real Qt widget), same
        derivation as the scratch prototype's own
        ``_screen_to_panel_local``, adjusted for this table's actual
        world placement: base-anchored on X at ``self._position.x``
        (world X range ``[self._position.x, self._position.x +
        self._scale.x]``), centered on Z (see :meth:`_table_screen_rect`'s
        own docstring on why X and Z are NOT symmetric here).

        *screen_pos* is LOGICAL pixels (``.x``/``.y`` -- see
        :meth:`_table_screen_rect`'s own docstring on both the screen-
        vs-world ``Point`` axis convention and the logical-vs-device
        pixel distinction); converted to DEVICE pixels before reaching
        ``camera.screen_to_world``, which expects that. World units here
        are millimeters, not logical pixels -- the hidden widget is
        built at ``mdi_host.PIXELS_PER_MM`` logical pixels per world-unit
        (see that constant's own comment, and ``PegboardTableHost.
        __init__``'s own ``sub_window.resize()``), so a world-space
        offset is scaled up by that same factor to land on the widget's
        own local pixel offset.

        The result is in :attr:`self._host` 's OWN coordinate space, not
        the sub-window's content-local space (0, 0 at the table's own
        top-left corner) -- every caller feeds this straight into
        ``self._host.childAt()``/``target.mapFrom(self._host, ...)``,
        both of which need a point in ``self._host``'s frame. The hosted
        sub-window itself no longer sits at local ``(0, 0)`` (see
        ``mdi_host.SUB_WINDOW_ANCHOR``'s own comment -- it rests at the
        middle of the oversized hidden area between interactions, not
        the origin), so the content-local offset computed below has to
        be shifted by that same anchor to land in the right place.
        Confirmed 2026-09-16: without this, every synthesized event's
        target point was off by the anchor's ~(1000, 700) px, so
        ``childAt``/``mapFrom`` never found the real widgets at all and
        no interaction reached the table.
        """
        camera = self.pegboard.camera
        dpr = camera.canvas.devicePixelRatio()

        device_screen_pos = _point.Point(screen_pos.x * dpr, screen_pos.y * dpr)
        world_pos = camera.screen_to_world(device_screen_pos)

        top_left_x = self._position.x
        top_left_z = self._position.z - (self._scale.z / 2.0)

        content_x = (world_pos.x - top_left_x) * _mdi_host.PIXELS_PER_MM
        content_y = (world_pos.z - top_left_z) * _mdi_host.PIXELS_PER_MM

        anchor = _mdi_host.SUB_WINDOW_ANCHOR
        return QtCore.QPointF(content_x + anchor.x(), content_y + anchor.y())

    @_check_types.do
    def _on_cursor_changed(self, cursor: QtGui.QCursor) -> None:
        self.pegboard.camera.canvas.setCursor(cursor)

    @_check_types.do
    def _on_close_requested(self) -> None:
        self.is_visible = False

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Arm/disarm this table as the canvas's own active handler for
        the WHOLE selected duration, not just while a press/drag
        happens to be in progress.

        ``mouse_handler_base.MouseHandlerBase._dispatch_to_active_
        handler`` only re-picks a fresh target for a real click-type
        event (by design -- not for MOVE, which fires on every pixel of
        movement). A plain hover-only MOVE with no button held is
        therefore routed ONLY via ``canvas.active_handler_obj``, never
        a fresh pick. Arming ``_active_handler`` on LEFT_DOWN only (the
        previous design here) meant hover forwarding, and wheel-scroll
        (whose own dispatch DOES re-pick, but only lands back on this
        table when the cursor happens to sit exactly over its AABB/OBB
        at that instant), both only actually worked in the narrow
        window between a press and its matching release -- confirmed
        2026-09-16 as "hovering is wrong" and "the wheel only sometimes
        scrolls the table, other times it zooms." Arming for the whole
        selected duration instead matches ``rotation_handlers.
        rotation_rings.RotationRings``'s own pattern (armed for as long
        as the gizmo is up, not per-drag), and the original design
        intent: "left click to select the table and that will create
        the handler."

        :meth:`handle_interaction` now uses :attr:`_press_target`
        (already maintained by :meth:`_dispatch_press`/
        :meth:`_dispatch_release`) instead of :attr:`_active_handler` to
        tell an in-progress drag apart from a plain hover, since
        :attr:`_active_handler` no longer means "currently pressed."
        """
        super().set_selected(flag)

        # BaseVar.set_selected sets self._is_opaque from self.
        # _selected_material.is_opaque -- Config.editor_pegboard.
        # selected_color has alpha 0.25, so selecting ANY pegboard
        # object normally flags it translucent. CanvasBase's shared
        # render loop routes a translucent SELECTED object through a
        # special deferred pass (glDepthMask(GL_FALSE) for its entire
        # render() call, meant for a 3D object's translucent outer
        # shell) -- wrong for this table, which never actually uses
        # that translucent highlight at all (see _render_selection_
        # border's own docstring: selection is shown as an opaque green
        # frame instead). With depth writes disabled for the whole
        # render() call, neither the table's own texture quad nor the
        # connecting line left real depth behind for each other or for
        # whatever rendered next to test against -- confirmed 2026-09-16
        # as "other objects/the connecting line still render on top of
        # the table" even after _render_connector's own material fix.
        # Forcing is_opaque back to 1 keeps this table on the normal,
        # non-deferred opaque render path regardless of selection.
        self._is_opaque[0] = 1

        if flag:
            self._active_handler = _TABLE_HANDLER
            self.pegboard.editor.active_handler_obj = self
        else:
            self._active_handler = None
            if self.pegboard.editor.active_handler_obj is self:
                self.pegboard.editor.active_handler_obj = None
            self._clear_hover()
            self._set_resize_cursor(None)
            self._resize_zone = None
            self._resize_fixed_x = None
            self._resize_fixed_z = None

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object,
    ) -> bool:
        """Forward mouse interaction into the hidden widget, only while
        this table is selected -- see module docstring and
        :meth:`set_selected` (armed for the whole selected duration,
        not per-press).
        """
        if not self.is_selected:
            return False

        Interaction = _interaction.MouseInteraction

        if interaction_type == Interaction.LEFT_DOWN:
            zone = self._resize_zone_at(current_pos)
            if zone is not None:
                self._start_resize(zone)
                return True

            if not self._point_in_table_rect(current_pos):
                return False

            self._dispatch_press(current_pos)
            return True

        if interaction_type == Interaction.LEFT_DCLICK:
            if not self._point_in_table_rect(current_pos):
                return False

            self._dispatch_double_click(current_pos)
            return True

        if interaction_type == Interaction.MOVE:
            if self._resize_zone is not None:
                self._apply_resize(current_pos)
                return True

            if self._press_target is not None:
                self._dispatch_drag_move(current_pos)
                return True

            # Not dragging -- the green selection border's own ring is
            # a resize handle (see _resize_zone_at); show the matching
            # cursor there and consume the event (blocking camera pan)
            # without forwarding anything into the hidden widget.
            zone = self._resize_zone_at(current_pos)
            if zone is not None:
                self._set_resize_cursor(zone)
                self._clear_hover()
                return True

            self._set_resize_cursor(None)

            # Forward as hover as long as the cursor is still within
            # the table's own rect, so native hover feedback (resize
            # cursors, button glow) works even without a button held.
            # Outside it, clear any stale hover and let this event fall
            # through to the default handling (camera pan, etc.)
            # unconsumed.
            if self._point_in_table_rect(current_pos):
                self._dispatch_hover(self._screen_to_panel_local(current_pos))
                return True

            self._clear_hover()
            return False

        if interaction_type == Interaction.LEFT_UP:
            if self._resize_zone is not None:
                self._resize_zone = None
                self._resize_fixed_x = None
                self._resize_fixed_z = None
                return True

            if self._press_target is None:
                return False

            self._dispatch_release(current_pos)
            return True

        if interaction_type == Interaction.CANCEL:
            if self._resize_zone is not None:
                # Abort the in-progress resize at whatever size/
                # position it had reached -- matches CANCEL's own
                # press/drag handling below (undo the grab, not the
                # partial change already applied), since there's no
                # separate "pre-resize" snapshot to roll back to and
                # every MOVE up to this point already committed via
                # _apply_resize.
                self._resize_zone = None
                self._resize_fixed_x = None
                self._resize_fixed_z = None
                return True

            if self._press_target is None:
                return False

            # Abort the in-progress press/drag only -- selection (and
            # this table's own arming, see set_selected) is untouched;
            # a CANCEL means the OS/Qt broke the mouse grab mid-drag,
            # not that the user deselected the table.
            self._press_target = None
            self._press_local = None
            return True

        return False

    @_check_types.do
    def handle_wheel(self, mouse_pos: _point.Point, qt_wheel_event, clicked_object) -> bool:
        """Forward a wheel event into the hidden table's own viewport,
        only while this table is selected -- see module docstring.
        """
        if not self.is_selected:
            return False

        if not self._point_in_table_rect(mouse_pos):
            return False

        panel_local = self._screen_to_panel_local(mouse_pos)
        target = self._host.table.viewport()
        local_point = target.mapFrom(self._host, panel_local.toPoint())
        global_point = target.mapToGlobal(local_point)

        wheel = QtGui.QWheelEvent(
            QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            qt_wheel_event.pixelDelta(), qt_wheel_event.angleDelta(),
            qt_wheel_event.buttons(), qt_wheel_event.modifiers(),
            qt_wheel_event.phase(), qt_wheel_event.inverted(), qt_wheel_event.source())
        wheel.setTimestamp(qt_wheel_event.timestamp())
        QtWidgets.QApplication.sendEvent(target, wheel)

        # Scrolling moves content under a cursor that hasn't itself
        # moved -- refresh hover state at the same screen position too
        # (see the scratch prototype's own wheelEvent for why).
        self._dispatch_hover(panel_local)

        self._regrab_texture()
        return True

    # ------------------------------------------------------------------
    # Synthetic event dispatch -- ported from the scratch prototype's
    # QTableTextureCanvas, same technique, different coordinate source.
    # ------------------------------------------------------------------

    @_check_types.do
    def _dispatch_hover(self, panel_local: QtCore.QPointF,
                        modifiers: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier) -> None:
        point = panel_local.toPoint()
        target = self._host.childAt(point)
        if target is None:
            # Every caller of _dispatch_hover/_dispatch_press/
            # _dispatch_double_click already confirmed (via
            # _point_in_table_rect) that this point is meant to be ON
            # the table, so a childAt() miss here means the point landed
            # on the sub-window's own title bar/border chrome -- not
            # covered by any nested child widget, but still part of
            # self._host.sub_window's own geometry -- not genuinely off
            # the whole panel. Falling back to self._host (the QMdiArea
            # itself) sent the event to the wrong widget entirely: a
            # click on the QMdiArea's own background does nothing, so
            # edge/corner resize (a target only a few pixels wide,
            # unlike the title bar's much more forgiving strip) could
            # never engage at all whenever rounding put the point even
            # slightly outside a nested child's rect. self._host.
            # sub_window is the correct fallback -- its own mouse
            # handling does the real move/resize edge hit-testing from
            # there.
            target = self._host.sub_window

        local_point = target.mapFrom(self._host, point)
        global_point = target.mapToGlobal(local_point)

        if target is not self._hover_target:
            if self._hover_target is not None:
                QtWidgets.QApplication.sendEvent(
                    self._hover_target, QtCore.QEvent(QtCore.QEvent.Type.Leave))

            enter = QtGui.QEnterEvent(
                QtCore.QPointF(local_point), QtCore.QPointF(global_point), QtCore.QPointF(global_point))
            QtWidgets.QApplication.sendEvent(target, enter)
            self._hover_target = target

        move = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton, modifiers)
        QtWidgets.QApplication.sendEvent(target, move)

        self._regrab_texture()

    @_check_types.do
    def _clear_hover(self) -> None:
        if self._hover_target is None:
            return

        QtWidgets.QApplication.sendEvent(
            self._hover_target, QtCore.QEvent(QtCore.QEvent.Type.Leave))
        self._hover_target = None
        self._regrab_texture()

    @_check_types.do
    def _dispatch_press(self, screen_pos: _point.Point) -> None:
        panel_local = self._screen_to_panel_local(screen_pos)
        point = panel_local.toPoint()
        target = self._host.childAt(point)
        if target is None:
            # See _dispatch_hover's own comment on why self._host.
            # sub_window, not self._host, is the correct fallback here.
            target = self._host.sub_window

        local_point = target.mapFrom(self._host, point)
        global_point = target.mapToGlobal(local_point)

        self._press_target = target
        self._press_local = local_point

        # A MouseMove to the target's own position must reach it before
        # the press -- QMdiSubWindow's mouseReleaseEvent (and the drag-
        # operation mousePressEvent arms) reads hoveredSubControl,
        # established only by a preceding hover move, not by the press
        # itself (confirmed empirically against Qt's own
        # qmdisubwindow.cpp source while building the scratch
        # prototype).
        hover = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, hover)

        press = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, press)

        self._regrab_texture()

    @_check_types.do
    def _dispatch_double_click(self, screen_pos: _point.Point) -> None:
        panel_local = self._screen_to_panel_local(screen_pos)
        point = panel_local.toPoint()
        target = self._host.childAt(point)
        if target is None:
            # See _dispatch_hover's own comment on why self._host.
            # sub_window, not self._host, is the correct fallback here.
            target = self._host.sub_window

        local_point = target.mapFrom(self._host, point)
        global_point = target.mapToGlobal(local_point)

        self._press_target = target
        self._press_local = local_point

        hover = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, hover)

        dbl_click = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonDblClick, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, dbl_click)

        self._regrab_texture()

    @_check_types.do
    def _dispatch_release(self, screen_pos: _point.Point) -> None:
        target = self._press_target
        if target is None:
            return

        panel_local = self._screen_to_panel_local(screen_pos)
        local_point = target.mapFrom(self._host, panel_local.toPoint())
        global_point = target.mapToGlobal(local_point)

        release = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, release)

        self._press_target = None
        self._press_local = None

        self._regrab_texture()

    @_check_types.do
    def _dispatch_drag_move(self, screen_pos: _point.Point) -> None:
        target = self._press_target
        if target is None:
            return

        panel_local = self._screen_to_panel_local(screen_pos)

        # Deliberately mapped through self._host (NOT clamped to
        # target's own rect) -- a real drag routinely carries the
        # cursor outside the widget that grabbed it (e.g. off the top
        # or bottom of a scrollbar track), and the grabbed widget is
        # expected to keep receiving accurate positions anyway, same as
        # a real OS-level mouse grab would deliver.
        local_point = target.mapFrom(self._host, panel_local.toPoint())
        global_point = target.mapToGlobal(local_point)
        self._press_local = local_point

        move = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove, QtCore.QPointF(local_point), QtCore.QPointF(global_point),
            QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier)
        QtWidgets.QApplication.sendEvent(target, move)

        self._regrab_texture()
