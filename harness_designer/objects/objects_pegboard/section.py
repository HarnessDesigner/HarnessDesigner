# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board concentric section widget -- Peg Board Editor view object.

Owns a hidden :class:`~ui.concentric_section.section_host.
ConcentricSectionHost` (the cross-section + wire information widget inside an
off-screen ``QMdiArea`` / ``QMdiSubWindow``), captures it to a GL texture, and
draws that texture on this object's own world-space quad through
``shaders.texture`` (``gl.shaders.program.TextureProgram``) -- the same
technique, and the same shared unit-quad VBO / position / scale, as
:class:`~.table.Table` (the floating wire table), which this is modelled on.
Read that module's docstring for the long story; what differs here:

- there is no owning anchor, so no connecting line and no anchor visibility
  to follow -- the widget belongs to a CONCENTRIC (``pjt_pegboard_sections.
  concentric_id``), which a bundle, a transition branch, or a connected pair
  of them shares;
- the synthetic mouse / wheel dispatch lives in the host (it needs no GL and
  can be tested without one); this object only turns a canvas pixel into a
  point in the host's frame and calls it;
- the quad is anchored like the table's: its position is the LEFT edge in X
  and the vertical MIDDLE in Z (``shapes.rectangle.create_vbo_based``).

As with the table, mouse interaction reaches the hidden widget only while this
object is the SELECTED one: an unselected section behaves like any other
peg-board object under the mouse.
"""

from typing import TYPE_CHECKING, Union as _Union

from OpenGL import GL
from PySide6 import QtCore, QtGui

from . import base_pegboard as _base_pegboard
from . import table as _table
from . import wire_drop as _wire_drop
from ...handlers import concentric_handler as _concentric_handler
from ...shapes import rectangle as _rectangle
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ...ui.concentric_section import section_host as _section_host
from ... import color as _color
from ... import check_types as _check_types
from ...crash_dump import Attr, capturable


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from .. import pegboard_section as _pegboard_section
    from ...database.project_db import pjt_pegboard_section as _pjt_pegboard_section
    from ...gl import shaders as _shaders
    from ...ui.concentric_section import section_model as _section_model
    from ...ui.concentric_section import section_widget as _section_widget


# The wire tables' own tuned look and feel -- the selection ring, the rounded
# corners, the resize grab margin and the resize cursors -- so the two kinds of
# floating panel select, resize and stack the same way.
_BORDER_DEPTH_OFFSET = _table._BORDER_DEPTH_OFFSET  # NOQA
_BOTTOM_CORNER_RADIUS_PX = _table._BOTTOM_CORNER_RADIUS_PX  # NOQA
_BORDER_THICKNESS_MM = _table._BORDER_THICKNESS_MM  # NOQA
_RESIZE_HIT_MARGIN_MM = _table._RESIZE_HIT_MARGIN_MM  # NOQA
_BORDER_CORNER_RADIUS_MM = _table._BORDER_CORNER_RADIUS_MM  # NOQA
_BORDER_RGBA = _table._BORDER_RGBA  # NOQA
_RESIZE_CURSOR_FOR_ZONE = _table._RESIZE_CURSOR_FOR_ZONE  # NOQA
_SECTION_HANDLER = _table._TABLE_HANDLER  # NOQA

# The ring drawn round a section while a wire is dragged over it (the selection ring is green).
_DROP_RGBA = bytes([255, 170, 0, 255])

# Never resize a section smaller than this, in world mm, on either axis -- the
# cross-section and the information pane together need about this much room.
_MIN_SECTION_SIZE_MM = 40.0


@_check_types.do
def _solid_texture(rgba: bytes) -> int:
    """A 1x1 opaque colour as a GL texture -- what a ring is drawn with through ``shaders.texture`` (its rounded-rect
    clip is what rounds the ring; see :meth:`Table._render_selection_border`). Needs the GL context current."""
    texture_id = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 1, 1, 0,
        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, rgba)
    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    return texture_id


@capturable()
class Section(_base_pegboard.BasePegboard):
    """Peg Board Editor representation of a concentric section widget -- not
    view-specific in the data (the 3D and schematic views hold inert
    placeholders); this module holds the peg-board view's implementation.
    """

    __dump_schema__ = (
        Attr('render_id', severity=1),
        Attr('_texture_id', severity=1),
    )

    db_obj: "_pjt_pegboard_section.PJTPegboardSection"

    # A section always wins picking against ordinary scene geometry, as it
    # always wins rendering (render()'s GL_ALWAYS), and ties with a wire table
    # are settled by render_id like two tables are.
    _pick_priority = 2

    # class-level default: set_selected can run before __init__ finishes
    _hover_cursor_active = False
    _wire_drop_hover = False

    @_check_types.do
    def __init__(self, parent: "_pegboard_section.PegboardSection",
                 db_obj: "_pjt_pegboard_section.PJTPegboardSection"):
        """Initialise the :class:`Section` instance.

        :param parent: Parent object.
        :type parent: :class:`_pegboard_section.PegboardSection`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_section.PJTPegboardSection`
        """
        width, height = db_obj.size

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

            # 0 until render() draws this section for the first time; see
            # Table._render_id_counter (shared with it, below)
            self.render_id = 0

            self._host = _section_host.ConcentricSectionHost(
                self._section_title(), width, height)
            self._texture_id = GL.glGenTextures(1)
            self._texture_px_size = (1, 1)

            # the green selection ring and the orange drop ring: 1x1 opaque
            # textures, drawn through shaders.texture for its rounded-rect
            # clip (see Table.__init__)
            self._border_texture_id = _solid_texture(_BORDER_RGBA)
            self._drop_texture_id = _solid_texture(_DROP_RGBA)
            self._border_angle = _angle.Angle()

        self._host.cursor_changed.connect(self._on_cursor_changed)
        self._host.close_requested.connect(self._on_close_requested)

        # Resize-via-the-green-border state -- see Table's own comment: the
        # zone an in-progress resize started on and the OPPOSITE (unmoving)
        # edges, frozen at press time so a drag measures from one anchor.
        self._resize_zone: tuple[str | None, str | None] | None = None
        self._resize_fixed_x: float | None = None
        self._resize_fixed_z: float | None = None
        self._resize_cursor_active = False
        self._hover_cursor_active = False

        _wire_drop.register(self)

        # shows what the concentric already holds
        self.reload()

    @_check_types.do
    def _section_title(self) -> str:
        """Title bar text: the bundle and / or the transition the shared
        concentric belongs to."""
        concentric = self.db_obj.concentric
        bundle = concentric.bundle
        branch = concentric.transition_branch

        if bundle is not None and branch is not None:
            return f'Concentric: {bundle.name} / {branch.transition.name}'

        if bundle is not None:
            return f'Concentric: {bundle.name}'

        if branch is not None:
            return f'Concentric: {branch.transition.name}'

        return 'Concentric twist'

    # ------------------------------------------------------------------
    # What the owner (the layout / database adapter) drives
    # ------------------------------------------------------------------

    @property
    @_check_types.do
    def widget(self) -> "_section_widget.ConcentricSectionWidget":
        """The hosted widget -- connect to its ``cable_moved`` /
        ``cable_move_finished`` / ``cable_selected`` signals to save a cable's
        new place."""
        return self._host.section

    @_check_types.do
    def set_section(self, spec: "_section_model.SectionSpec") -> None:
        """Show a cross-section and refresh the texture."""
        self._host.section.set_section(spec)
        self._regrab_texture()

    @_check_types.do
    def set_wire_details(self, details: dict) -> None:
        """Set what the information pane shows for each wire (by cable key)
        and refresh the texture."""
        self._host.section.set_wire_details(details)
        self._regrab_texture()

    @_check_types.do
    def refresh(self) -> None:
        """Re-capture the texture (after anything changed the widget from the
        outside)."""
        self._regrab_texture()

    @_check_types.do
    def reload(self) -> None:
        """Show what this section's concentric holds now: its cables and each
        wire's details (``handlers.concentric_handler.build_section``), planning
        the layout first if two wires are still on the same spot."""
        db = self.db_obj.table.db
        concentric = self.db_obj.concentric

        if _concentric_handler.needs_plan(concentric):
            _concentric_handler.replan(db, concentric)

        spec, details = _concentric_handler.build_section(concentric)
        self._host.section.set_section(spec)
        self._host.section.set_wire_details(details)
        self._regrab_texture()

    # ------------------------------------------------------------------
    # A wire dragged out of a wire table lands here (objects_pegboard.wire_drop)
    # ------------------------------------------------------------------

    @_check_types.do
    def wire_drop_contains(self, screen_pos: _point.Point) -> bool:
        """Whether the pointer (logical canvas pixels) is over this section."""
        return self.is_visible and self._point_in_rect(screen_pos)

    @_check_types.do
    def set_wire_drop_hover(self, flag: bool) -> None:
        """Show or hide the ring that says a wire can be dropped here."""
        self._wire_drop_hover = flag
        self.pegboard.Refresh()

    @_check_types.do
    def accept_wire_drop(self, wire_id: bytes) -> bool:
        """Add the wire to this section's concentric and show it.

        :returns: ``False`` if the wire was already in the concentric.
        """
        db = self.db_obj.table.db
        added = _concentric_handler.add_wire(db, self.db_obj.concentric, db.pjt_wires_table[wire_id])

        if added:
            self.reload()

        return added

    # ------------------------------------------------------------------
    # Texture capture / upload
    # ------------------------------------------------------------------

    @_check_types.do
    def _regrab_texture(self) -> None:
        """Capture the hidden widget and upload it as this object's live GL
        texture, folding a title-bar drag or an edge resize of the hosted
        sub-window into the world position and size first (see
        :meth:`Table._regrab_texture`, whose reasoning for each step this
        follows, including why the upload runs inside ``pegboard.context``)."""
        delta = self._host.sub_window_moved()
        if delta.x() or delta.y():
            # the delta is in the HOST's logical pixels; world units are mm
            host_dpr = self._host.devicePixelRatio()
            with self._position:
                self._position.x += (float(delta.x()) / host_dpr) / _section_host.PIXELS_PER_MM
                self._position.z += (float(delta.y()) / host_dpr) / _section_host.PIXELS_PER_MM

            # `with point:` does not fire the bound callbacks on exit; this is
            # the shared, DB-backed point, so firing them is what persists it
            self._position._process_callbacks()  # NOQA

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

        # The hosted widget's own pixel size is the source of truth for the
        # world footprint (a native sub-window resize changes IT, not
        # self._scale): keep them in step and persist, as a drag persists the
        # position through the bound Point.
        host_dpr = self._host.devicePixelRatio()
        world_w = (width / host_dpr) / _section_host.PIXELS_PER_MM
        world_h = (height / host_dpr) / _section_host.PIXELS_PER_MM
        if (self._scale.x, self._scale.z) != (world_w, world_h):
            with self._scale:
                self._scale.x = world_w
                self._scale.z = world_h

            self.db_obj.size = (world_w, world_h)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the captured widget texture on this object's own quad.

        Reuses :meth:`_render_geometry` exactly as ``BaseVar.render`` does for
        ``shaders.faces`` -- it reads ``self._vbo`` / ``_position`` /
        ``_angle`` / ``_scale`` and sets the program's uniforms -- so the only
        thing specific to a textured quad is binding the GL texture around it.
        """
        if not self.is_visible:
            return

        if self._vbo is None:
            return

        self._aabb_manager.mark_visible(self._aabb_index)
        self._obb_manager.mark_visible(self._obb_index)

        # One counter for every floating panel (the wire tables' own), so a
        # section and a table stacked on each other are ranked consistently.
        _table.Table._render_id_counter += 1  # NOQA
        self.render_id = _table.Table._render_id_counter  # NOQA

        # the orange drop ring wins over the green selection ring while a wire is over it
        if self._wire_drop_hover:
            self._render_selection_border(shaders, self._drop_texture_id)
        elif self.is_selected:
            self._render_selection_border(shaders, self._border_texture_id)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)

        # Always on top of ordinary scene geometry whatever was drawn before it
        # this frame (see Table.render for why GL_LESS alone is not enough).
        GL.glDepthFunc(GL.GL_ALWAYS)
        with shaders.texture:
            shaders.texture.quad_size_px = self._texture_px_size
            shaders.texture.corner_radius_px = (
                0.0, 0.0, _BOTTOM_CORNER_RADIUS_PX, _BOTTOM_CORNER_RADIUS_PX)
            shaders.texture.ring_thickness_px = 0.0
            shaders.texture.bottom_corner_trim_px = 0.0
            self._render_geometry(shaders.texture)
        GL.glDepthFunc(GL.GL_LESS)

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    @_check_types.do
    def _render_selection_border(self, shaders: "_shaders.ShaderProgram", texture_id: int) -> None:
        """A fully opaque rounded RING just outside this section's quad, in
        world mm (so it scales with the zoom), drawn through
        ``shaders.texture`` against the 1x1 colour texture *texture_id*
        (green for selected, orange for a wire dragged over it) -- see
        :meth:`Table._render_selection_border`."""
        thickness = _BORDER_THICKNESS_MM

        position = _point.Point(
            self._position.x - thickness,
            self._position.y + _BORDER_DEPTH_OFFSET,
            self._position.z)
        scale = _point.Point(
            self._scale.x + (2.0 * thickness), 1.0,
            self._scale.z + (2.0 * thickness))

        angle = _rectangle.create_vbo_based().render_angle(self._border_angle)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)

        GL.glDepthFunc(GL.GL_ALWAYS)
        with shaders.texture:
            shaders.texture.quad_size_px = (scale.x, scale.z)
            shaders.texture.corner_radius_px = _BORDER_CORNER_RADIUS_MM
            shaders.texture.ring_thickness_px = thickness
            shaders.texture.bottom_corner_trim_px = 0.0
            _rectangle.create_vbo_based().render(shaders.texture, position, angle, scale, None)
        GL.glDepthFunc(GL.GL_LESS)

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    # ------------------------------------------------------------------
    # Canvas pixel <-> world <-> the hidden widget
    # ------------------------------------------------------------------

    @_check_types.do
    def _section_screen_rect(self) -> tuple[float, float, float, float]:
        """This section's on-screen rect, in LOGICAL canvas pixels, from its
        live world position and scale. The quad is anchored on its LEFT edge
        in X (``[position.x, position.x + scale.x]``) but centred in Z -- see
        :meth:`Table._table_screen_rect` for the axis and device-pixel
        details.

        :returns: ``(left, top, right, bottom)``.
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
    def _point_in_rect(self, screen_pos: _point.Point) -> bool:
        left, top, right, bottom = self._section_screen_rect()
        return left <= screen_pos.x <= right and top <= screen_pos.y <= bottom

    @_check_types.do
    def _screen_to_world(self, screen_pos: _point.Point) -> _point.Point:
        """Logical canvas pixels -> world."""
        camera = self.pegboard.camera
        dpr = camera.canvas.devicePixelRatio()
        device_screen_pos = _point.Point(screen_pos.x * dpr, screen_pos.y * dpr)
        return camera.screen_to_world(device_screen_pos)

    @_check_types.do
    def _screen_to_panel_local(self, screen_pos: _point.Point) -> QtCore.QPointF:
        """Logical canvas pixels -> a point in the HOST's own coordinate
        frame: world offset from the quad's top-left, times
        ``PIXELS_PER_MM``, shifted by ``SUB_WINDOW_ANCHOR`` (the sub-window
        rests mid-way into the oversized hidden area, not at its origin) --
        see :meth:`Table._screen_to_panel_local`."""
        world_pos = self._screen_to_world(screen_pos)

        top_left_x = self._position.x
        top_left_z = self._position.z - (self._scale.z / 2.0)

        content_x = (world_pos.x - top_left_x) * _section_host.PIXELS_PER_MM
        content_y = (world_pos.z - top_left_z) * _section_host.PIXELS_PER_MM

        anchor = _section_host.SUB_WINDOW_ANCHOR
        return QtCore.QPointF(content_x + anchor.x(), content_y + anchor.y())

    # ------------------------------------------------------------------
    # Resize through the green border
    # ------------------------------------------------------------------

    @_check_types.do
    def _resize_zone_at(self, screen_pos: _point.Point) -> tuple[str | None, str | None] | None:
        """Classify *screen_pos* against the resize-grab zone around the
        section (its footprint grown by ``_RESIZE_HIT_MARGIN_MM`` on every
        side), in WORLD space -- see :meth:`Table._resize_zone_at`.

        :returns: ``None`` inside the footprint or beyond the margin;
            otherwise ``(x_edge, z_edge)``, each ``'min'`` / ``'max'`` /
            ``None``; both set is a corner.
        """
        world_pos = self._screen_to_world(screen_pos)

        margin = _RESIZE_HIT_MARGIN_MM
        min_x = self._position.x
        max_x = self._position.x + self._scale.x
        min_z = self._position.z - (self._scale.z / 2.0)
        max_z = self._position.z + (self._scale.z / 2.0)

        if not (min_x - margin <= world_pos.x <= max_x + margin and
                min_z - margin <= world_pos.z <= max_z + margin):
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
        """Show the resize cursor for *zone*, or release this object's cursor
        override when it is ``None``."""
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
        """Begin a resize drag in *zone*, freezing the OPPOSITE edge(s)."""
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
        """Resize to track *screen_pos* during a drag started by
        :meth:`_start_resize`: new footprint from the frozen edges (clamped to
        ``_MIN_SECTION_SIZE_MM``), applied to the live position, the REAL
        sub-window resized to match, then re-grabbed -- whose size sync
        reconciles the scale against whatever the widget actually came out at
        (it has a minimum size of its own)."""
        world_pos = self._screen_to_world(screen_pos)
        x_edge, z_edge = self._resize_zone

        if x_edge == 'min':
            new_width = max(_MIN_SECTION_SIZE_MM, self._resize_fixed_x - world_pos.x)
            new_x = self._resize_fixed_x - new_width
        elif x_edge == 'max':
            new_width = max(_MIN_SECTION_SIZE_MM, world_pos.x - self._resize_fixed_x)
            new_x = self._resize_fixed_x
        else:
            new_width = self._scale.x
            new_x = self._position.x

        if z_edge == 'min':
            new_height = max(_MIN_SECTION_SIZE_MM, self._resize_fixed_z - world_pos.z)
            new_center_z = self._resize_fixed_z - (new_height / 2.0)
        elif z_edge == 'max':
            new_height = max(_MIN_SECTION_SIZE_MM, world_pos.z - self._resize_fixed_z)
            new_center_z = self._resize_fixed_z + (new_height / 2.0)
        else:
            new_height = self._scale.z
            new_center_z = self._position.z

        with self._position:
            self._position.x = new_x
            self._position.z = new_center_z
        self._position._process_callbacks()  # NOQA

        width_px = max(1, int(new_width * _section_host.PIXELS_PER_MM))
        height_px = max(1, int(new_height * _section_host.PIXELS_PER_MM))
        self._host.resize_sub_window(width_px, height_px)

        self._regrab_texture()

    @_check_types.do
    def _end_resize(self) -> None:
        self._resize_zone = None
        self._resize_fixed_x = None
        self._resize_fixed_z = None

    # ------------------------------------------------------------------
    # Cursors
    # ------------------------------------------------------------------

    @_check_types.do
    def _on_cursor_changed(self, cursor: QtGui.QCursor) -> None:
        self.pegboard.camera.canvas.setCursor(cursor)
        self._hover_cursor_active = True

    @_check_types.do
    def _mirror_cursor(self) -> None:
        """Make the canvas's cursor match the widget under the pointer (the
        hosted widgets only announce a CHANGE, never a pointer that merely
        left one that kept its cursor -- see :meth:`Table._mirror_cursor`)."""
        cursor = self._host.hover_cursor()

        if cursor.shape() == QtCore.Qt.CursorShape.ArrowCursor:
            self._reset_hover_cursor()
            return

        self.pegboard.camera.canvas.setCursor(cursor)
        self._hover_cursor_active = True

    @_check_types.do
    def _reset_hover_cursor(self) -> None:
        """Release whatever cursor a hosted widget put on the canvas -- only
        if this object set one."""
        if not self._hover_cursor_active:
            return

        self._hover_cursor_active = False
        if not self._resize_cursor_active:
            self.pegboard.camera.canvas.unsetCursor()

    @_check_types.do
    def _on_close_requested(self) -> None:
        """The title bar's close button: hide the widget (the row and its
        position / size stay)."""
        self.is_visible = False

    # ------------------------------------------------------------------
    # Selection and mouse interaction -- only while selected
    # ------------------------------------------------------------------

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Arm / disarm this section as the canvas's active handler for the
        WHOLE selected duration (a hover-only MOVE is routed only through
        ``active_handler_obj``) -- see :meth:`Table.set_selected`, including
        why ``_is_opaque`` is forced back to 1 (the translucent selection tint
        would push this through the deferred pass with depth writes off)."""
        super().set_selected(flag)

        self._is_opaque[0] = 1

        if flag:
            self._active_handler = _SECTION_HANDLER
            self.pegboard.editor.active_handler_obj = self
        else:
            self._active_handler = None
            if self.pegboard.editor.active_handler_obj is self:
                self.pegboard.editor.active_handler_obj = None

            self._reset_hover_cursor()
            self._clear_hover()
            self._set_resize_cursor(None)
            self._end_resize()

    @_check_types.do
    def _dispatch_hover(self, panel_local: QtCore.QPointF) -> None:
        self._host.dispatch_hover(panel_local)
        self._mirror_cursor()
        self._regrab_texture()

    @_check_types.do
    def _clear_hover(self) -> None:
        self._host.clear_hover()
        self._regrab_texture()

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None],
    ) -> bool:
        """Forward mouse interaction into the hidden widget, only while this
        section is selected (see :meth:`set_selected`)."""
        if not self.is_selected:
            return False

        Interaction = _interaction.MouseInteraction

        if interaction_type == Interaction.LEFT_DOWN:
            zone = self._resize_zone_at(current_pos)
            if zone is not None:
                self._start_resize(zone)
                return True

            if not self._point_in_rect(current_pos):
                return False

            self._host.dispatch_press(self._screen_to_panel_local(current_pos))
            self._regrab_texture()
            return True

        if interaction_type == Interaction.LEFT_DCLICK:
            if not self._point_in_rect(current_pos):
                return False

            self._host.dispatch_double_click(self._screen_to_panel_local(current_pos))
            self._regrab_texture()
            return True

        if interaction_type == Interaction.MOVE:
            if self._resize_zone is not None:
                self._apply_resize(current_pos)
                return True

            if self._host.has_press():
                self._host.dispatch_drag_move(self._screen_to_panel_local(current_pos))
                self._regrab_texture()
                return True

            # Not dragging: the green ring is a resize handle -- show the
            # matching cursor and consume the event (blocking a camera pan)
            zone = self._resize_zone_at(current_pos)
            if zone is not None:
                self._set_resize_cursor(zone)
                self._clear_hover()
                return True

            self._set_resize_cursor(None)

            # Within the section: forward as hover, so native hover feedback
            # (the sash cursor, the close button's glow) works. Outside it,
            # drop any stale hover and let the event fall through unconsumed.
            if self._point_in_rect(current_pos):
                self._dispatch_hover(self._screen_to_panel_local(current_pos))
                return True

            self._reset_hover_cursor()
            self._clear_hover()
            return False

        if interaction_type == Interaction.LEFT_UP:
            if self._resize_zone is not None:
                self._end_resize()
                return True

            if not self._host.has_press():
                return False

            self._host.dispatch_release(self._screen_to_panel_local(current_pos))
            self._regrab_texture()
            return True

        if interaction_type == Interaction.CANCEL:
            if self._resize_zone is not None:
                # abort at whatever size it reached -- every MOVE already committed
                self._end_resize()
                return True

            if not self._host.has_press():
                return False

            # abort the press / drag only; the selection is untouched (a CANCEL
            # means the grab was broken mid-drag, not that the user deselected)
            self._host.cancel_press()
            return True

        return False

    @_check_types.do
    def handle_wheel(self, mouse_pos: _point.Point, qt_wheel_event: "QtGui.QWheelEvent",
                     clicked_object: _Union["_ObjectBase", None]) -> bool:
        """Scroll the information pane when the wheel is over it, only while
        selected. Over the rest of the widget the wheel is NOT consumed, so
        the camera still zooms."""
        if not self.is_selected:
            return False

        if not self._point_in_rect(mouse_pos):
            return False

        panel_local = self._screen_to_panel_local(mouse_pos)
        if not self._host.dispatch_wheel(panel_local, qt_wheel_event):
            return False

        # scrolling moves content under a pointer that has not itself moved
        self._host.dispatch_hover(panel_local)
        self._regrab_texture()
        return True

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    @_check_types.do
    def _delete(self) -> None:
        self._reset_hover_cursor()
        self._set_resize_cursor(None)

        _wire_drop.unregister(self)

        # unlike the wire table, free what this object allocated: its GL
        # textures and the hidden host
        with self.pegboard.context:
            GL.glDeleteTextures([self._texture_id, self._border_texture_id, self._drop_texture_id])

        self._host.deleteLater()

        super()._delete()
