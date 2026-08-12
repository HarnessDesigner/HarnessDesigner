# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import uuid as _uuid_module

import numpy as np
import build123d
from PySide6.QtWidgets import QMenu
from OpenGL import GL

from . import base_schematic as _base_schematic
from ...ui.widgets import context_menus as _context_menus
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...geometry import point as _point
from ...shapes import text as _text
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor2d

_ALIGN_BOTTOM_LEFT = [build123d.TextAlign.LEFT, build123d.TextAlign.BOTTOM]
_ALIGN_BOTTOM_RIGHT = [build123d.TextAlign.RIGHT, build123d.TextAlign.BOTTOM]


@_check_types.do
def _bracket_vbo():
    """Return (building it first if not already cached) the shared "("
    bracket VBO every terminal shares -- always the same single character
    at the same font size, so one pooled VBO (a deterministic key, not a
    per-instance UUID, so every ``Terminal`` resolves to the same cached
    instance) covers every terminal's row instead of rebuilding an
    identical mesh per instance. See ``gl.vbo.PooledVBOHandler``/
    ``VBOSingleton``'s weakref-cache semantics -- stays alive as long as
    at least one ``Terminal`` instance holds a reference, freed
    automatically once the last one is deleted.
    """
    font_size = Config.label.bracket_font_size
    return _text.create_vbo(f'terminal-bracket-{font_size}', '(', font_size,
                            text_align=_ALIGN_BOTTOM_RIGHT)


# TODO add render function

class Terminal(_base_schematic.BaseSchematic):
    """
    2D representation of a terminal for schematic view

    Renders this terminal's own name (LEFT/BOTTOM-aligned text sitting
    just inside its owning housing's rectangle, near the pin edge) as its
    primary VBO, plus the "(" bracket as an extra (see
    :meth:`render_extras`) at a fixed local offset just outside the pin
    edge -- on the VBO/shader pipeline (see ``objects_schematic/base_schematic.py``'s
    ``BaseSchematic``), matching how ``Base3D`` subclasses render.
    ``position2d``/``angle2d`` are computed and persisted by the owning
    ``objects_schematic/housing.py``'s ``Housing`` whenever its layout changes
    (see ``Housing._layout_children``) -- this class only reacts to its
    own name changing, to rebuild its text mesh in place.
    """
    _parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal"

    @_check_types.do
    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """Initialise the :class:`Terminal` instance.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """
        self._part = db_obj.part

        # _mesh_args()/_build() (below) read self.db_obj -- set it before
        # that first call, same as objects_3d/note.py's Note.__init__ does
        # (BaseSchematic.__init__, which normally sets this, doesn't run until
        # after _build() since the VBO it builds is one of its own args).
        self.db_obj = db_obj

        # This terminal's own id into shapes.text's VBO registry --
        # generated and owned here, exactly like objects_3d/note.py's
        # Note._text_uuid.
        self._text_uuid = str(_uuid_module.uuid4())

        position = db_obj.position2d
        angle = db_obj.angle2d
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            vbo, _width, _height = self._build()
            self._bracket_vbo, _bracket_width, _bracket_height = _bracket_vbo()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self._name_cb = self.db_obj.bind(self._rebuild, 'name')

    @_check_types.do
    def _mesh_args(self) -> dict:
        return dict(text=self.db_obj.name, font_size=Config.label.terminal_name_font_size,
                    text_align=_ALIGN_BOTTOM_LEFT)

    @_check_types.do
    def _build(self):
        """Build this terminal's name VBO (construction time only -- see
        :meth:`_rebuild` for in-place content updates).

        :returns: ``(vbo, width, height)``.
        """
        return _text.create_vbo(self._text_uuid, **self._mesh_args())

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Rebuild this terminal's name mesh in place from its current
        name and re-derive its OBB/AABB (``self._vbo.update`` recomputes
        the VBO's own ``local_obb``/``local_aabb``, but that doesn't by
        itself propagate to this object's world-space ``obb``/``aabb`` --
        see ``BaseVar._compute_obb``/``_compute_aabb``). Bound to fire
        whenever this terminal's own name changes.
        """
        with self.editor2d.editor.context:
            vertices, faces, _width, _height = _text.create(**self._mesh_args())
            packed, count = _utils.compute_normals(vertices, faces)
            self._vbo.update(packed, count)
            self._compute_obb()
            self._compute_aabb()

        self.editor2d.Refresh()

    @_check_types.do
    def render_extras(self, program, pos_loc, rot_loc, scale_loc, normal_loc):
        """Render the "(" bracket under the already-bound schematic2d
        *program*, at a fixed local offset just outside the pin edge
        from this terminal's own name position -- called by
        ``gl.canvas2d.canvas.Canvas._render_vbo_objects`` right after
        this terminal's own name.
        """
        if self._position is None:
            return

        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        GL.glUniform1i(normal_loc, 0)
        GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)

        label_material = _materials.Generic(_color.Color(*Config.colors.label))
        label_material.set(program)

        # Mirrors the housing-local offset between row_local_x/
        # outside_local_x objects_schematic/housing.py's Housing._layout_children
        # placed this terminal's own name at -- the bracket sits that
        # same distance further out, past the pin edge.
        bracket_local_x = -(Config.label.outside_offset + Config.label.padding)
        wx, wy, wz = self._world_offset(bracket_local_x, 0.0)
        GL.glUniform3f(pos_loc, self._position.x + wx, wy, self._position.z + wz)
        self._bracket_vbo.render()

    @_check_types.do
    def _world_offset(self, local_x: float, local_z: float) -> tuple[float, float, float]:
        """Rotate a ``(local_x, 0, local_z)`` offset by this terminal's
        current ``angle2d.y`` -- see ``objects_schematic/housing.py``'s own
        ``_world_offset`` (same math, same reason).
        """
        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        x, y, z = _base_schematic._rotate_about_y(points, self._angle.y)[0]  # NOQA
        return float(x), float(y), float(z)

    @_check_types.do
    def _delete(self):
        self._name_cb.unbind()
        self._detach_extra_wires_at_position2d()
        super()._delete()

    @_check_types.do
    def get_context_menu(self):
        """Return this terminal's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_2d``, which calls
        this on whatever ``objschematic`` was right-clicked) -- notably the
        entry point for drawing a wire from the schematic editor (see
        :meth:`TerminalMenu.on_add_wire`).
        """
        return TerminalMenu(self.editor2d.editor, self)

    @_check_types.do
    def _detach_extra_wires_at_position2d(self):
        """Give every wire but the first one attached at this terminal's
        own 2D point its own new point at the same coordinates.

        Unlike 3D, a terminal has no separate crimp/layout-point chain
        in the schematic view -- wires attach directly to the
        terminal's own position2d, and seals aren't rendered in 2D at
        all, so there's nothing else to clean up here. Only the first
        wire found keeps the shared point (it becomes uniquely its own
        once the terminal row is gone); every additional wire would
        otherwise stay joined to it through a point that no longer
        represents a real connection.
        """
        ptables = self.mainframe.project.ptables
        point_id = self.db_obj.position2d_id

        if point_id is None:
            return

        x, y, _ = ptables.pjt_points2d_table[point_id].point.as_float
        seen_first = False

        for column in ('start_point2d_id', 'stop_point2d_id'):
            for row in ptables.pjt_wires_table.select('id', **{column: point_id}):
                wire_db = ptables.pjt_wires_table[row[0]]

                if not seen_first:
                    seen_first = True
                    continue

                new_point = ptables.pjt_points2d_table.insert(x, y)
                attr = column.replace('_point2d_id', '_position2d_id')
                setattr(wire_db, attr, new_point.db_id)


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects_schematic.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`TerminalMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_wire(self):
        """Start the interactive 2D wire-drawing flow (see
        ``handlers/wire_handler_2d.py``), pinned to this terminal as the
        start end.
        """
        from ..objects_3d import menu_ops as _menu_ops
        from ...handlers import wire_handler_2d as _wire_handler_2d

        mainframe = self.selected.mainframe
        terminal_obj = self.selected.parent

        _menu_ops.start_handler(
            mainframe,
            lambda: _wire_handler_2d.AddWireHandler2D(mainframe, terminal=terminal_obj))

    @_check_types.do
    def on_add_wire_service_loop(self):
        """Handle the add wire service loop event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
