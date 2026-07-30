# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import uuid as _uuid_module

import numpy as np
import build123d
from PySide6.QtWidgets import QMenu
from OpenGL import GL

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import rectangle as _rectangle
from ...shapes import text as _text
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


Config = _config.Config.editor2d


class Housing(_base2d.Base2D):
    """
    2D representation of a housing for schematic view

    Renders as a colored rectangle (unit primitive from ``shapes.rectangle``,
    scaled) plus its own corner label (name/part number/manufacturer), via
    the schematic2d shader/VBO pipeline (see ``objects2d/base2d.py``'s
    ``Base2D``) -- matches how ``Base3D`` subclasses render, no immediate-
    mode fallback. Sizing is fixed (``Config.editor2d.housing.width`` for
    the text-axis extent, ``num_cavities * Config.editor2d.cavity.height``
    for the cavity-axis extent), not measured from any label text.

    Every cavity's name, and (for cavities with a seated terminal) the "("
    bracket and the terminal's name, are rendered independently by their
    own ``objects2d/cavity.py``'s ``Cavity``/``objects2d/terminal.py``'s
    ``Terminal`` -- each a real, individually selectable ``Base2D``
    object with its own OBB/AABB. This class only computes *where* those
    live (see :meth:`_layout_children`) and persists it to their own
    ``position2d``/``angle2d``, whenever the sorted cavity order or seated-
    terminal set changes -- Cavity/Terminal pick the new values up
    automatically through the same bound-Point callback every other
    ``BaseVar`` position/angle update already uses.
    """
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        self._part = db_obj.part

        # Nothing built yet -- _recompute()'s first call, below, needs
        # these to already exist.
        self._db_callbacks = []
        self._corner_label_vbo = None

        position = db_obj.position2d
        angle = db_obj.angle2d

        # TODO: Lock a hsouing to only be able to be rotated in 90° increments.
        #       this also means the same thing would apply to terminals and also
        #       to cavities.

        material = _materials.Generic(_color.Color(*Config.colors.housing))

        # Every GL call below (the rectangle's own VBO, the corner-label
        # text VBO _recompute() builds, and Base2D.__init__'s own
        # vbo.acquire()) needs a current context -- acquired once here and
        # held for all of it.
        with parent.mainframe.editor2d.editor.context:
            vbo = _rectangle.create_vbo()

            # self._position/._angle don't exist until Base2D.__init__ (below)
            # runs, so _recompute takes this housing's own position/angle
            # explicitly rather than reading self -- see _layout_children.
            cavity_extent, text_extent = self._recompute(db_obj, position, angle)

            scale = _point.Point(text_extent, 1.0, cavity_extent)

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    def _recompute(self, db_obj, position: _point.Point, angle: _angle.Angle
                   ) -> tuple[float, float]:
        """(Re)compute this housing's fixed cavity-axis extent, rebuild
        the corner label, push every cavity's/seated terminal's own
        world position2d/angle2d (see :meth:`_layout_children`), and
        (re)bind the DB callbacks that trigger the next recompute (a
        cavity's name changes -- reordering its slot -- or a cavity
        gains/loses its terminal). Shared by ``__init__`` (the first
        build) and :meth:`_rebuild` (every one after). Requires a
        current GL context.

        :param position: This housing's own ``position2d`` -- taken as a
            parameter rather than read from ``self._position`` since
            ``__init__`` calls this before ``Base2D.__init__`` has set
            that attribute yet.
        :param angle: This housing's own ``angle2d``, same reason.
        :returns: ``(cavity_extent, text_extent)`` -- ``text_extent`` is
            now fixed (``Config.editor2d.housing.width``), returned only
            so ``__init__``/:meth:`_rebuild`'s scale-setting code stays
            uniform.
        """
        self._release_corner_label()
        self._unbind_callbacks()

        # Sorted by the cavity's own *name* -- the user-facing identifier
        # (can be numeric, alphabetic, or mixed; that's exactly why the
        # name field exists rather than relying on the catalog cavity's
        # idx, which is purely internal bookkeeping and never shown).
        cavities = sorted(
            (c for c in db_obj.cavities if c is not None),
            key=lambda c: c.name)

        cavity_extent = self._compute_cavity_extent(len(cavities))
        text_extent = Config.housing.width

        # Cached for _update_position/_update_angle below, so moving/
        # rotating this housing (drag, or housing_layout.py's own
        # auto-placement) can re-run _layout_children without re-sorting
        # from scratch on every mutation.
        self._sorted_cavities = cavities
        self._cavity_extent = cavity_extent
        self._text_extent = text_extent

        self._layout_children(cavities, cavity_extent, text_extent, position, angle)
        self._build_corner_label(db_obj, cavity_extent, text_extent)

        self._bind_callbacks(cavities)

        return cavity_extent, text_extent

    def _update_position(self, position: _point.Point):
        """Re-run :meth:`_layout_children` after the inherited OBB/AABB
        update -- a housing's cavities/terminals are positioned in
        absolute world space (not relative to the housing at render
        time), so moving the housing (drag, or
        ``objects2d/housing_layout.py``'s own auto-placement) must push
        fresh positions to them, not just recompute this housing's own
        bounds.
        """
        super()._update_position(position)
        self._layout_children(
            self._sorted_cavities, self._cavity_extent, self._text_extent,
            position, self._angle)

    def _update_angle(self, angle: _angle.Angle):
        """See :meth:`_update_position` -- same reason, for rotation."""
        super()._update_angle(angle)
        self._layout_children(
            self._sorted_cavities, self._cavity_extent, self._text_extent,
            self._position, angle)

    def _rebuild(self, _entry=None):
        """Re-run :meth:`_recompute` and update this housing's live scale
        from the result -- bound (see :meth:`_bind_callbacks`) to fire
        whenever a cavity's name changes (reordering slots) or a cavity
        gains/loses its terminal, so the schematic never needs a manual
        refresh to pick those up.
        """
        with self.editor2d.editor.context:
            cavity_extent, text_extent = self._recompute(
                self.db_obj, self._position, self._angle)

            with self._scale:
                self._scale.x = text_extent
                self._scale.z = cavity_extent

        self.editor2d.Refresh()

    def _bind_callbacks(self, cavities):
        """Bind every DB callback that should trigger :meth:`_rebuild`:
        each cavity's own name (its sort order, and so its slot, can
        change) and each cavity's ``'terminal_id'`` (a synthetic tag --
        see ``PJTTerminalsTable.insert``/``PJTTerminal.delete``/the
        ``cavity_id`` setter in ``database/project_db/pjt_terminal.py``
        -- fired when a terminal is seated/unseated/moved between
        cavities, since there's no real ``terminal_id`` column on
        ``pjt_cavities`` to bind to directly). A seated terminal's own
        name no longer matters here -- it doesn't affect this housing's
        fixed-size layout, and ``objects2d/terminal.py``'s ``Terminal``
        handles its own name-change rebuild independently.
        """
        for cavity in cavities:
            self._db_callbacks.append(cavity.bind(self._rebuild, 'name'))
            self._db_callbacks.append(cavity.bind(self._rebuild, 'terminal_id'))

    def _unbind_callbacks(self):
        for cb in self._db_callbacks:
            cb.unbind()

        self._db_callbacks = []

    def _release_corner_label(self):
        if self._corner_label_vbo is not None:
            self._corner_label_vbo.release()

        self._corner_label_vbo = None

    def _delete(self):
        self._unbind_callbacks()
        super()._delete()

    @staticmethod
    def _compute_cavity_extent(n: int) -> float:
        """Cavity-axis (local Z) extent for *n* cavities -- fixed slot
        size, stacked edge-to-edge with no gap (see
        ``Config.editor2d.cavity``); never individually drawn.
        """
        cavity_cfg = Config.cavity

        if n <= 0:
            return cavity_cfg.height

        return n * cavity_cfg.height

    def _layout_children(self, cavities, cavity_extent, text_extent,
                         position: _point.Point, angle: _angle.Angle):
        """Compute and persist each cavity's/seated terminal's own world
        ``position2d``/``angle2d`` from the current sorted slot order --
        ``objects2d/cavity.py``'s ``Cavity``/``objects2d/terminal.py``'s
        ``Terminal`` pick the new values up automatically (each already
        has its own position/angle bound to trigger its inherited
        ``BaseVar._update_position``/``_update_angle``, which recomputes
        its own OBB/AABB) -- no direct call into either needed here.

        Layout (local X = text/width axis, local Z = cavity/height axis;
        canonical/unrotated pose = this housing on the right edge of the
        schematic, pin edge at local X = -text_extent/2; cavity slots
        stack top-to-bottom in ascending sort order, i=0 at the top --
        the standard pinout-diagram reading convention):

        - Cavity name anchor: a small amount outside the housing
          rectangle (past the pin edge), a fixed gap above the
          bracket's own vertical center rather than flush with the
          slot's own top edge (RIGHT/BOTTOM-aligned text, so this point
          is exactly its own bottom-right corner).
        - Terminal name anchor: only when a terminal is seated, *inside*
          the housing rectangle (near the pin edge), bottom edge flush
          with the slot's bottom boundary (LEFT/BOTTOM-aligned text, so
          this point is exactly its own bottom-left corner --
          ``objects2d/terminal.py``'s ``Terminal`` renders the "("
          bracket as an extra at a fixed local offset from this same
          point, RIGHT/BOTTOM-aligned to sit just outside the pin edge).
        """
        label_cfg = Config.label
        cavity_height = Config.cavity.height

        half_cavity_extent = cavity_extent / 2.0
        half_text_extent = text_extent / 2.0
        pin_local_x = -half_text_extent          # pin edge -- interior-facing side
        cavity_local_x = pin_local_x - label_cfg.cavity_outside_offset
        terminal_local_x = pin_local_x + label_cfg.padding

        for i, cavity in enumerate(cavities):
            # i=0 (the first, ascending-sorted cavity) gets the TOP-most
            # slot, so cavities read top-to-bottom in ascending order --
            # the standard pinout-diagram convention. i * cavity_height
            # descends from there (each subsequent cavity moves down).
            slot_top = half_cavity_extent - i * cavity_height
            slot_bottom = slot_top - cavity_height

            # BOTTOM/RIGHT-aligned (see objects2d/cavity.py's Cavity),
            # anchored a fixed gap above the bracket's own vertical
            # center -- not the slot's own top edge, which would read as
            # part of the row above it.
            cavity_name_z = slot_bottom + label_cfg.bracket_font_size / 2.0 + label_cfg.cavity_name_gap
            self._place_child(cavity, cavity_local_x, cavity_name_z, position, angle)

            terminal = cavity.terminal
            if terminal is not None and terminal.name:
                self._place_child(terminal, terminal_local_x, slot_bottom, position, angle)

    @staticmethod
    def _place_child(child_db_obj, local_x: float, local_z: float,
                     housing_position: _point.Point, housing_angle: _angle.Angle):
        """Write *child_db_obj*'s own ``position2d``/``angle2d`` from a
        housing-local ``(local_x, local_z)`` offset -- same rotate-then-
        translate math as ``objects2d/housing_layout.py``'s own
        ``_apply_placement``, and the same bound-Point write path.
        """
        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        wx, _wy, wz = _base2d._rotate_about_y(points, housing_angle.y)[0]  # NOQA

        position = child_db_obj.position2d
        with position:
            position.x = housing_position.x + float(wx)
            position.z = housing_position.z + float(wz)

        child_db_obj.angle2d.y = housing_angle.y

    def _build_corner_label(self, db_obj, cavity_extent, text_extent):
        """(Re)build the corner label (name/part number/manufacturer),
        this housing's own -- not a cavity's/terminal's -- extra.
        """
        label_cfg = Config.label

        _ALIGN_BOTTOM_RIGHT = [build123d.TextAlign.RIGHT, build123d.TextAlign.BOTTOM]

        corner_text = f'{db_obj.name}\n{self._part.part_number}\n{self._part.manufacturer.name}'
        self._corner_label_vbo, _corner_width, _corner_height = _text.create_vbo(
            str(_uuid_module.uuid4()), corner_text, label_cfg.corner_font_size,
            text_align=_ALIGN_BOTTOM_RIGHT)

        half_text_extent = text_extent / 2.0
        half_cavity_extent = cavity_extent / 2.0

        corner_local_x = half_text_extent - label_cfg.padding
        corner_local_z = -half_cavity_extent + label_cfg.padding

        # RIGHT/BOTTOM-aligned (see _ALIGN_BOTTOM_RIGHT above), so this
        # point IS the label's own bottom-right corner -- no width/height
        # offset math needed to keep it from overflowing.
        self._corner_label_local = (corner_local_x, corner_local_z)

    def render_extras(self, program, pos_loc, rot_loc, scale_loc, normal_loc):
        """Render this housing's own corner label (name/part number/
        manufacturer) under the already-bound schematic2d *program* --
        called by ``gl.canvas2d.canvas.Canvas._render_vbo_objects`` right
        after this housing's own rectangle. Cavity names and terminal
        brackets/names are rendered independently by
        ``objects2d/cavity.py``'s ``Cavity``/``objects2d/terminal.py``'s
        ``Terminal`` -- their own position2d/angle2d are kept in sync by
        :meth:`_layout_children` above.
        """
        if self._position is None or self._corner_label_vbo is None:
            return

        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        GL.glUniform1i(normal_loc, 0)
        GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)

        label_material = _materials.Generic(_color.Color(*Config.colors.label))
        label_material.set(program)

        local_x, local_z = self._corner_label_local
        wx, wy, wz = self._world_offset(local_x, local_z)
        GL.glUniform3f(pos_loc, self._position.x + wx, wy, self._position.z + wz)
        self._corner_label_vbo.render()

    def _world_offset(self, local_x: float, local_z: float) -> tuple[float, float, float]:
        """Rotate a ``(local_x, 0, local_z)`` offset by this housing's
        current ``angle2d.y`` (about world Y -- the axis a Y=0-flat 2D
        primitive must spin about to stay flat; the source that writes
        it, ``objects2d/housing_layout.py``, is what controls this, not
        this method) -- see ``objects2d/base2d.py``'s ``_rotate_about_y``.
        """
        points = np.array([[local_x, 0.0, local_z]], dtype=np.float32)
        x, y, z = _base2d._rotate_about_y(points, self._angle.y)[0]  # NOQA
        return float(x), float(y), float(z)

    def hit_test(self, world_pos: _point.Point) -> bool:
        """
        Test if point is inside the housing rectangle (accounting for
        rotation), using the text-axis/cavity-axis extents computed in
        :meth:`_recompute`.
        """
        if self._position is None:
            return False

        local_x = world_pos.x - self._position.x
        local_z = world_pos.z - self._position.z

        rotation_rad = -math.radians(self._angle.y)
        cos_a = math.cos(rotation_rad)
        sin_a = math.sin(rotation_rad)

        rotated_x = local_x * cos_a - local_z * sin_a
        rotated_z = local_x * sin_a + local_z * cos_a

        return (abs(rotated_x) <= self._text_extent / 2 and
                abs(rotated_z) <= self._cavity_extent / 2)

    def move_to(self, world_x: float, world_y: float):
        """
        Move housing to new position. Cavity/terminal positions cascade
        automatically via :meth:`_update_position`'s
        :meth:`_layout_children` call -- no separate push needed here.
        """
        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.z = world_y


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects2d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
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

    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_terminal(self):
        """Handle the add terminal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_cpa_lock(self):
        """Handle the add CPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_tpa_lock(self):
        """Handle the add TPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_cover(self):
        """Handle the add cover event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_boot(self):
        """Handle the add boot event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
