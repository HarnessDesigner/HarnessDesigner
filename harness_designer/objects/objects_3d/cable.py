# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The 3D view of a placed cable (``TWISTED_WIRE_DESIGN.md`` section 8a).

A cable's trunk is drawn exactly as a wire is, so this subclasses the 3D wire view and reuses all of it: the path, the
mitred bends, and, for a part that ``is_twisted``, the twisted conductors. What differs is small:

* its ends are always free (the facade has no sibling), so a wire's crimp-end look never shows;
* it is not tied to the peg-board slack handler (its peg-board view, :mod:`~harness_designer.objects.objects_pegboard.cable`,
  is seeded from this route and has no slack: nothing attaches to a cable);
* a click on it only selects it: dragging an end or a waypoint of an existing cable is not built yet;
* its menu and its placement are its own (:meth:`Cable.start_add_cable`,
  :mod:`~harness_designer.add_handlers.editor_3d.cable`).

A cable is drawn by its style (``Wire.cable_style`` of the part): TWISTED as the wire view draws a twisted pair; RIBBON as a
flat strip of touching round conductors side by side (``shapes.twisted_wire.ribbon_profile``, a rate-0 look through the same
shader), turned about its axis by the cable's ``roll_deg`` and carried round bends by parallel transport, so its flat side keeps
its direction; JACKETED as one round tube (at the part's ``od_mm``, or the diameter that holds its conductors when there is
none).
"""

from typing import TYPE_CHECKING, Iterator, Union as _Union
from typing import NamedTuple as _NamedTuple

import math

import numpy as np
from PySide6 import QtCore, QtWidgets

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import twisted_wire as _twisted_wire
from ...gl import materials as _materials
from . import wire as _wire_3d
from ..mixins import tube as _tube
from . import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ... import check_types as _check_types
from ...crash_dump import capturable


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from .. import cable as _cable
    from ...database.project_db import pjt_cable as _pjt_cable
    from ...ui.editor_3d import editor_3d as _editor_3d
    from ... import ui as _ui


FAN_ANGLE_DEG = 20.0
"""The angle from the cable's axis at which the outermost conductor leaves when the cable is split: the split is the cross-section
at the split plane projected onto the cable's true end from a light behind it, and this is how steep the light's cone is."""


def fan_scale(radius: float, split: float) -> float:
    """How much the cross-section of a split end grows when it is projected from the split plane onto the cable's true end.

    The light sits on the cable's axis behind the plane, at the distance where the outermost conductor (*radius* from the axis)
    is seen at :data:`FAN_ANGLE_DEG`; the screen is *split* mm beyond the plane, so everything on it is ``(reach + split) / reach``
    times as far from the axis as it is in the plane. So the outermost lead always leaves at the same angle, whatever the cable's or
    the conductors' diameter (a thin cable's cross-section is magnified more than a thick one's).

    :param radius: How far the outermost conductor centre is from the axis, mm.
    :param split: The distance from the split plane to the cable's true end, mm.
    """
    if radius < 1e-9:
        return 1.0

    reach = radius / math.tan(math.radians(FAN_ANGLE_DEG))

    return (reach + split) / reach

MIN_SPLIT_MM = 1.0
"""The shortest distance from the end that a split can be at."""

MIN_TRUNK_MM = 2.0
"""The shortest stretch of the end segment that must stay as the cable's own trunk."""


class _Slot(_NamedTuple):
    """Where one conductor (or the shield) of a cable sits in its cross-section."""

    x: float
    """Where the conductor sits in the cable, across, mm (in the frame of the trunk's end segment)."""

    y: float
    """Where it sits, up, mm."""


@capturable()
class Cable(_wire_3d.Wire):
    """The 3D view of a placed cable."""

    parent: "_cable.Cable" = None
    db_obj: "_pjt_cable.PJTCable" = None

    _start_split: float = 0.0
    _stop_split: float = 0.0
    _slots: list[_Slot] = None

    # a ribbon cable: its segments with the roll of its flat side in their angle (cleared by _recalculate_geometry)
    _ribbon: bool = False
    _rolled: list = None

    @staticmethod
    @_check_types.do
    def _trunk_size(part: object) -> tuple[float, float]:
        """How wide and how thick the trunk is drawn: a ribbon is ``count * pitch`` by one pitch, any other cable round (see
        ``Wire.trunk_size``).

        :param part: The cable's catalog wire.
        """
        return part.trunk_size

    @_check_types.do
    def _make_look(self, diameter: float) -> _Union[_tube.TwistLook, None]:
        """A twisted cable's look as the wire's; a ribbon's is a row of conductors; any other cable is a plain tube.

        :param diameter: The cable's diameter, mm.
        """
        if self._part.is_ribbon:
            return self._build_ribbon()

        return super()._make_look(diameter)

    @_check_types.do
    def reload_look(self) -> None:
        """Draw the trunk again after the part's conductors were edited (their colours are the catalog's, so the change is global)."""
        self._ribbon = False
        self._twist = self._make_look(self._trunk_size(self._part)[0])
        self.reload_splits()

    @_check_types.do
    def _build_ribbon(self) -> _tube.TwistLook:
        """The look of a ribbon cable: its conductors in a row across the trunk (``shapes.twisted_wire.ribbon_profile``), no
        twist. Colours come from the part's conductor rows; a part without them is drawn in the cable's colour."""
        part = self._part
        count = len(part.conductors) or max(1, part.num_conductors)
        pitch = part.ribbon_pitch_mm

        if len(part.conductor_colors) == count:
            materials, stripes = self._conductor_materials()
        else:
            materials = [_materials.Plastic(part.color.ui) for _ in range(count)]
            stripes = [None] * count

        self._ribbon = True

        return _tube.TwistLook(0.0, count * pitch * 0.5, _twisted_wire.ribbon_profile(count, pitch), materials, stripes, False)

    @_check_types.do
    def _recalculate_geometry(self) -> None:
        """As the wire's; a ribbon's rolled segments are worked out again with the path."""
        self._rolled = None
        super()._recalculate_geometry()

    @_check_types.do
    def _update_position(self, _: _Union[_point.Point, None]) -> None:
        """As the wire's, then keep the split points of a split end on the trunk's split plane: a waypoint of the route moved by a
        drag (or any other change of the route) turns or shifts the trunk's end, and the leads end at those points."""
        super()._update_position(_)
        self.parent.sync_split_ends()

    @_check_types.do
    def reload_roll(self) -> None:
        """Draw the ribbon again after its ``roll_deg`` changed."""
        self._recalculate_geometry()
        self.editor3d.Refresh()

    @_check_types.do
    def _segment_transforms(self) -> Iterator[tuple[_point.Point, _angle.Angle, _point.Point, float]]:
        """As the wire's; for a ribbon each segment's angle is turned about its direction by the roll of the flat side there
        (the cable's ``roll_deg`` at the start, carried round every bend by parallel transport), so the flat side is the
        segment's local X and the picking boxes are the strip's, and the shader needs no phase."""
        if not self._ribbon:
            yield from super()._segment_transforms()
            return

        if self._rolled is None:
            self._rolled = self._roll_segments(list(super()._segment_transforms()))

        yield from self._rolled

    @_check_types.do
    def _roll_segments(self, segments: list[tuple]) -> list[tuple]:
        """The wire's segments with the angle of each turned by the ribbon's roll there.

        :param segments: ``(position, angle, scale, length)`` per segment as the wire view yields them.
        """
        if not segments:
            return []

        rotations = [angle.as_matrix_numpy for _position, angle, _scale, _length in segments]
        lengths = [length for _position, _angle_, _scale, length in segments]
        twists = _twisted_wire.plan(rotations, lengths, self._segment_joins(segments), 0.0, self._twist.outer_radius,
                                    math.radians(float(self.db_obj.roll_deg)))
        result = []

        for (position, angle, scale, length), rotation, twist in zip(segments, rotations, twists):
            if twist.phase != 0.0:
                angle = _angle.Angle.from_matrix(_twisted_wire.rolled(rotation, twist.phase))

            result.append((position, angle, scale, length))

        return result

    @_check_types.do
    def reload_splits(self) -> None:
        """Read the split distances and the conductors again after a split or a join. A split end of the cable lies AT the split
        plane (the trunk ends there; the conductors go on as wires of their own, the cable's leads), and the split distance is how
        far beyond it the cable's end was before it was split: where the conductors' ends fan out from."""
        self._start_split = float(self.db_obj.start_split_mm)
        self._stop_split = float(self.db_obj.stop_split_mm)
        self._slots = self._build_slots()

        self._recalculate_geometry()
        self.editor3d.Refresh()

    @_check_types.do
    def _build_slots(self) -> list[_Slot]:
        """One :class:`_Slot` per conductor row of the cable, then its shield.

        The conductors sit where the twisted look puts them (``shapes.twisted_wire.profile``), the same circles whether or
        not the cable is drawn twisted; a shield comes out of the jacket at the bottom.
        """
        conductors = list(self.db_obj.conductors)

        if not conductors:
            return []

        regular = [conductor for conductor in conductors if not conductor.is_shield]
        diameter = self._part.trunk_size[0] or 1.0

        if self._twist is not None and len(self._twist.circles) == len(regular):
            circles = list(self._twist.circles)
        elif len(regular) == 1:
            circles = [(0.0, 0.0, diameter * 0.3)]
        elif regular:
            circles = _twisted_wire.profile(len(regular), diameter)
        else:
            circles = []

        slots = []
        index = 0

        for conductor in conductors:
            if conductor.is_shield:
                slots.append(_Slot(0.0, -diameter * 0.5))
            else:
                if index >= len(circles):
                    break

                x, y, _radius = circles[index]
                index += 1

                slots.append(_Slot(x, y))

        return slots

    @_check_types.do
    def _lead_frames(self) -> dict[bool, tuple[np.ndarray, np.ndarray, float]]:
        """Where the conductors leave the trunk: for the start (True) and the stop (False) end, the world position of the
        trunk's axis at the split plane, the rotation of the trunk's end segment (columns are its axes) and the angle the
        conductors have turned through by then (0 for a cable that is not twisted)."""
        if self._twist is not None:
            rate = self._twist.rate
            segments = [(np.asarray(s.position), s.matrix, s.length, s.twist.phase) for s in self._twist_segments()]
        else:
            rate = 0.0
            segments = [(position.as_numpy, angle.as_matrix_numpy, length, 0.0)
                        for position, angle, _scale, length in self._segment_transforms()]

        if not segments:
            return {}

        position, rotation, _length, phase = segments[0]
        frames = {True: (position, rotation, phase)}

        position, rotation, length, phase = segments[-1]
        frames[False] = (position + rotation[:, 2] * length, rotation, phase + rate * length)

        return frames

    @_check_types.do
    def fan_out_positions(self, start: bool) -> list[np.ndarray]:
        """Where each conductor's end lands when the *start* (or stop) end of the cable is split: the cross-section at the split plane
        (the conductors' centres, :meth:`split_positions`) projected onto the cable's true end (the split distance beyond the plane,
        out along the end segment) as if lit from a point on the axis behind it, so the projection is bigger (:func:`fan_scale`).
        In conductor order (shield last). The places are fixed (one per conductor row); which conductor takes which is its
        ``start_order`` / ``stop_order`` (by default its ``idx``, so each lands straight out from where it sits)."""
        frames = self._lead_frames()

        if start not in frames or not self._slots:
            return []

        # The cross-section at the plane, turned by the twist like the conductors in it (the same angle as split_positions, so each
        # conductor's end lands straight out from where it leaves the trunk and no two leads cross)
        position, rotation, theta = frames[start]
        cosine = math.cos(theta)
        sine = math.sin(theta)

        split = self._start_split
        outward = -rotation[:, 2]

        if not start:
            split = self._stop_split
            outward = rotation[:, 2]

        base = position + outward * split
        scale = fan_scale(max(math.hypot(slot.x, slot.y) for slot in self._slots), split)

        places = [base + rotation @ np.array([scale * (cosine * slot.x - sine * slot.y), scale * (sine * slot.x + cosine * slot.y), 0.0])
                  for slot in self._slots]

        orders = [conductor.start_order if start else conductor.stop_order for conductor in self.db_obj.conductors]

        # an order that is not a permutation of the places (a part with a different conductor count, a half-written change)
        # is ignored rather than guessed at
        if len(orders) == len(places) and sorted(orders) == list(range(len(places))):
            return [places[order] for order in orders]

        return places

    @_check_types.do
    def split_positions(self, start: bool) -> list[np.ndarray]:
        """Where each conductor leaves the trunk at the split plane of the *start* (or stop) end: its place in the cable
        there, turned by the twist, so that the lead meets the conductor without a jump. In conductor order (shield last).
        Only meaningful while that end is split."""
        frames = self._lead_frames()

        if start not in frames or not self._slots:
            return []

        base, rotation, theta = frames[start]
        cosine = math.cos(theta)
        sine = math.sin(theta)

        return [base + rotation @ np.array([cosine * slot.x - sine * slot.y, sine * slot.x + cosine * slot.y, 0.0])
                for slot in self._slots]

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Call after the cable's own waypoint rows change so the live callbacks, the cached length and the geometry
        catch up. As the wire's, without the slack handler (which a cable does not have)."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.editor3d.Refresh()

    @_check_types.do
    def add_waypoint(self, position: _point.Point, insert_idx: int) -> None:
        """Add a waypoint to the cable's route at *position*, as the *insert_idx*-th (the segment of the route it lies on, as
        ``get_closest_point`` gives it), and have the cable catch up. A cable has no layout at its waypoints: the route is
        just the point, which the rounded corner is drawn round.

        :param position: Where the waypoint goes, on the straight route.
        :param insert_idx: How many of the cable's waypoints come before it.
        """
        ptables = self.mainframe.project.ptables
        point = ptables.pjt_points3d_table.insert(float(position.x), float(position.y), float(position.z))

        ptables.pjt_cable_paths_table.add(self.db_obj.db_id, '3d', insert_idx, point.db_id)

        self.refresh_waypoints()

    @_check_types.do
    def _delete_waypoint(self, point: _point.Point) -> None:
        """Remove one waypoint of the cable's route: a cable has no layouts at its waypoints, so the point comes out of the route
        and is deleted itself (the route is renumbered), then the cable catches up."""
        ptables = self.mainframe.project.ptables
        point_id = point.db_id[:-2]

        ptables.pjt_cable_paths_table.remove(self.db_obj.db_id, '3d', point_id)
        ptables.pjt_points3d_table[point_id].delete()

        self.refresh_waypoints()

    @classmethod
    @_check_types.do
    def start_add_cable(cls, mainframe: "_ui.MainFrame", canvas: "_editor_3d.Editor3DPanel",
                        part_id: bytes) -> "_cable.Cable":
        """Begin placing a cable of the catalog wire *part_id* in free space.

        Builds the cable at a placeholder start point and arms the placement session
        (:class:`~harness_designer.add_handlers.editor_3d.cable.Cable`), which relocates it to the cursor. Same
        shape as the wire's free-space start. The cable has no conductors until the session finishes, when
        ``PJTCableConductorsTable.insert_for_cable`` makes them from its final end points.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param canvas: The 3D editor panel.
        :type canvas: :class:`_editor_3d.Editor3DPanel`
        :param part_id: The catalog wire (``Wire.is_cable`` is true for it).
        :type part_id: bytes
        :returns: The new cable's facade.
        :rtype: :class:`_cable.Cable`
        """
        from .. import cable as _cable_facade  # NOQA -- avoid a cycle at import time
        from ...add_handlers.editor_3d import cable as _add_cable  # NOQA -- avoid a cycle at import time

        ptables = mainframe.project.ptables
        part = mainframe.global_db.wires_table[part_id]

        start_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        stop_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        name = f'{part.manufacturer.name} {part.part_number}'

        cable_db = ptables.pjt_cables_table.insert(
            part_id, name, start_db.db_id, stop_db.db_id, None, None, True, True)

        facade = _cable_facade.Cable(mainframe, cable_db)

        # hidden until the first click sets the start: the stop point stays at the origin through phase 0, so a visible
        # cable would be drawn from the origin to the cursor (the session shows it once the end being placed follows the cursor)
        facade.obj3d.is_visible = False

        handler = _add_cable.Cable(
            canvas, facade, part_id, phase=0, growing_point=facade.obj3d.start_position, start_circuit_id=None)

        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def get_context_menu(self) -> "CableMenu":
        """Return the context menu.

        :rtype: :class:`CableMenu`
        """
        return CableMenu(self.mainframe.editor3d.editor, self)

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Forward to the placement session while there is one; otherwise drag the cable as a wire is dragged (a click and drag
        on the selected cable's body moves what the click is near: a free end, the two waypoints round the segment, or the whole
        cable, see ``drag_handlers.editor_3d.cable``); a plain click falls through to the default select / deselect.

        :param last_pos: Where the mouse was.
        :type last_pos: :class:`_point.Point`
        :param current_pos: Where it is.
        :type current_pos: :class:`_point.Point`
        :param had_motion: Whether the mouse moved since the press.
        :type had_motion: bool
        :param interaction_type: What happened.
        :type interaction_type: :class:`_interaction.MouseInteraction`
        :param clicked_object: The object under the mouse.
        :type clicked_object: :class:`_ObjectBase` | None
        :returns: Whether the interaction was handled.
        :rtype: bool
        """
        from ...add_handlers.editor_3d import cable as _add_cable  # NOQA -- avoid a cycle at import time
        from ...drag_handlers.editor_3d import cable as _drag_cable  # NOQA -- avoid a cycle at import time

        if self._waypoint_drag:
            return self._handle_waypoint_drag(last_pos, current_pos, interaction_type)

        handler = self._active_handler

        if isinstance(handler, _add_cable.Cable):
            # a local reference: finishing the session can delete this cable, which clears self._active_handler
            handled = handler(last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        if handler is not None:
            if interaction_type is _interaction.MouseInteraction.MOVE:
                handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                handler.delete()
                self._active_handler = None
                # no real drag happened: let a plain click-release fall through to the default select / deselect
                return had_motion

            return False

        if (
            interaction_type is not _interaction.MouseInteraction.LEFT_DOWN or
            clicked_object is not self.parent or
            self.parent.mainframe.get_selected() is not self.parent
        ):
            return False

        # a press on one of this object's waypoint handles drags that waypoint (objects/mixins/waypoint_handles.py)
        if self._arm_waypoint_drag(current_pos):
            return True

        plan = _drag_cable.Cable.plan_wire_drag(self.mainframe.project, self.parent, current_pos)

        if plan is None:
            return False

        self._active_handler = _drag_cable.Cable(self.editor3d.editor, self.parent, plan)
        return True


class CableMenu(QtWidgets.QMenu):
    """The context menu of a placed cable. The peg board's (``objects_pegboard.cable``) is this one with the roll left out."""

    # a ribbon can be turned about its length in 3D; lying flat on the peg board it has no roll
    _has_roll: bool = True

    # a waypoint is placed in the 3D editor (add_handlers/editor_3d/wire_layout.py); the peg board's menu leaves the entry out
    _has_add_layout: bool = True

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", selected: Cable):
        """Initialise the :class:`CableMenu` instance.

        :param canvas: The 3D editor panel.
        :type canvas: :class:`_editor_3d.Editor3DPanel`
        :param selected: The cable's 3D view.
        :type selected: :class:`Cable`
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        if self._has_add_layout:
            action = self.addAction('Add Layout')
            action.setToolTip('Add a waypoint to the cable')
            action.triggered.connect(self.on_add_layout)

        action = self.addAction('Delete Layout')
        action.setEnabled(bool(selected._waypoint_points))  # NOQA
        action.setToolTip('Remove the waypoint nearest the right click')
        action.triggered.connect(self.on_delete_layout)

        self.addSeparator()

        cable = selected.parent
        self._start = self._nearer_start()
        end_name = 'start' if self._start else 'stop'

        if cable.is_split(self._start):
            action = self.addAction(f'Join Conductors ({end_name} end)')
            action.setEnabled(cable.can_join(self._start))
            action.triggered.connect(self.on_join)
        else:
            action = self.addAction(f'Split Conductors ({end_name} end)')
            action.setEnabled(bool(cable.db_obj.conductors) and cable.max_split_mm(self._start) >= MIN_SPLIT_MM)
            action.triggered.connect(self.on_split)

        action = self.addAction(f'Fan-out Order ({end_name} end)...')
        action.setEnabled(len(cable.db_obj.conductors) > 1 and cable.can_reorder(self._start))
        action.triggered.connect(self.on_fan_out)

        if self._has_roll and cable.db_obj.part.is_ribbon:
            action = self.addAction('Roll Ribbon...')
            action.setEnabled(cable.can_roll())
            action.setToolTip('Turn the ribbon about its length. Join the conductors at both ends first.')
            action.triggered.connect(self.on_roll)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

    @_check_types.do
    def _click_world(self) -> _Union[np.ndarray, None]:
        """Where the right click was, in the world (``None`` when the menu was opened some other way)."""
        click_pos = self.selected._context_menu_click_pos  # NOQA

        return None if click_pos is None else click_pos.as_numpy

    @_check_types.do
    def _nearer_start(self) -> bool:
        """Whether the end the menu was opened at is the cable's start: the end nearer the right click (the start when
        there was no click position)."""
        click = self._click_world()

        if click is None:
            return True

        to_start = float(np.linalg.norm(self.selected.start_position.as_numpy - click))
        to_stop = float(np.linalg.norm(self.selected.stop_position.as_numpy - click))

        return to_start <= to_stop

    @_check_types.do
    def on_add_layout(self) -> None:
        """Start the interactive waypoint placement (``add_handlers/editor_3d/wire_layout.py``, as for a wire), seeded at the
        point of the cable that was right-clicked (the middle of the cable when the menu was opened some other way)."""
        from . import wire_layout as _wire_layout_3d  # NOQA -- avoid a cycle at import time

        mainframe = self.selected.mainframe
        cable = self.selected.parent

        click_pos = self.selected._context_menu_click_pos  # NOQA
        initial_pos = None

        if click_pos is not None:
            initial_pos, _angle, _insert_idx = self.selected.get_closest_point(click_pos)

        if initial_pos is None:
            middle = (self.selected.start_position.as_numpy + self.selected.stop_position.as_numpy) * 0.5
            initial_pos = _point.Point(*middle.tolist())

        @_check_types.do
        def _do() -> None:
            _wire_layout_3d.WireLayout.start_add(mainframe, cable, initial_pos)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_delete_layout(self) -> None:
        """Remove the waypoint nearest the right click that opened this menu."""
        self.selected.delete_closest_waypoint(self.selected._context_menu_click_pos)  # NOQA

    @_check_types.do
    def on_split(self) -> None:
        """Ask how far from the end the conductors split apart, and split them there."""
        cable = self.selected.parent
        start = self._start
        canvas = self.canvas

        limit = cable.max_split_mm(start)
        default = min(limit * 0.5, max(20.0, 6.0 * cable.db_obj.part.trunk_size[0]))
        end_name = 'start' if start else 'stop'

        @_check_types.do
        def _do() -> None:
            value, ok = QtWidgets.QInputDialog.getDouble(
                canvas, 'Split Conductors', f'Distance from the {end_name} end where the conductors leave the cable (mm):',
                default, MIN_SPLIT_MM, limit, 1)

            if ok:
                cable.split_end(start, value)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_fan_out(self) -> None:
        """Ask for the order the conductors of this end fan out in, and apply it."""
        cable = self.selected.parent
        start = self._start
        mainframe = self.selected.mainframe

        @_check_types.do
        def _do() -> None:
            from ...ui.dialogs import fan_out_order as _fan_out_order  # NOQA -- avoid a cycle at import time

            ordered = cable.fan_order(start)
            dialog = _fan_out_order.FanOutOrderDialog(
                mainframe, 'start' if start else 'stop', [cable.conductor_label(conductor) for conductor in ordered])

            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                cable.set_fan_order(start, [ordered[index] for index in dialog.GetValue()])

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_roll(self) -> None:
        """Ask how far to turn the ribbon about its length, and turn it."""
        cable = self.selected.parent
        canvas = self.canvas
        current = float(cable.db_obj.roll_deg)

        @_check_types.do
        def _do() -> None:
            value, ok = QtWidgets.QInputDialog.getDouble(
                canvas, 'Roll Ribbon', 'Turn of the ribbon about its length at its start (degrees):',
                current, -180.0, 180.0, 1)

            if ok:
                cable.set_roll(value)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_join(self) -> None:
        """Bring the conductors of this end back into the cable."""
        cable = self.selected.parent
        start = self._start

        @_check_types.do
        def _do() -> None:
            cable.join_end(start)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_select(self) -> None:
        """Make this cable the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this cable from the project."""
        _menu_ops.delete_object(self.selected)
