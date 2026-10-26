# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""QPainter drawing of one cable's cross-section.

The painter is already in millimetres (the caller translated to the cable's
centre and scaled), so every length here is a model value.

- A single insulated conductor: the insulation disc (the wire's OD, its
  primary colour), the stripe's cross-section if it has one, and the metal
  conductor disc in the middle.
- A twisted group of conductors (no shield, no jacket): each conductor drawn
  that way, packed together.
- A jacketed cable: jacket disc, shield ring if it has one, the core fill, and
  the conductors on top.
- A coax is the same drawing: one conductor whose "insulation" is the
  dielectric, then the shield ring and the jacket.
"""

from PySide6 import QtCore
from PySide6 import QtGui

from . import section_model as _section_model
from ... import check_types as _check_types


# A stripe cross-section: how many degrees of the circumference it covers, and
# how much of the insulation wall (conductor to OD) it goes down through.
STRIPE_ARC_DEG = 36.0
STRIPE_DEPTH_FRACTION = 0.45

_OUTLINE_ALPHA = 130
_BRAID_ALPHA = 90


@_check_types.do
def _color(rgb: tuple[int, int, int]) -> QtGui.QColor:
    return QtGui.QColor(rgb[0], rgb[1], rgb[2])


@_check_types.do
def _outline_pen() -> QtGui.QPen:
    """A 1 pixel outline that stays 1 pixel at any scale."""
    pen = QtGui.QPen(QtGui.QColor(0, 0, 0, _OUTLINE_ALPHA))
    pen.setCosmetic(True)
    pen.setWidthF(1.0)
    return pen


@_check_types.do
def _disc(painter: QtGui.QPainter, x: float, y: float, radius: float,
          rgb: tuple[int, int, int]) -> None:
    painter.setPen(_outline_pen())
    painter.setBrush(_color(rgb))
    painter.drawEllipse(QtCore.QPointF(x, y), radius, radius)


@_check_types.do
def _stripe_path(x: float, y: float, outer_radius: float, inner_radius: float,
                 start_deg: float, sweep_deg: float) -> QtGui.QPainterPath:
    """The stripe's cross-section: a piece of the insulation ring."""
    outer = QtCore.QRectF(x - outer_radius, y - outer_radius, 2.0 * outer_radius, 2.0 * outer_radius)
    inner = QtCore.QRectF(x - inner_radius, y - inner_radius, 2.0 * inner_radius, 2.0 * inner_radius)

    path = QtGui.QPainterPath()
    path.arcMoveTo(outer, start_deg)
    path.arcTo(outer, start_deg, sweep_deg)
    path.arcTo(inner, start_deg + sweep_deg, -sweep_deg)
    path.closeSubpath()
    return path


@_check_types.do
def paint_conductor(painter: QtGui.QPainter, x: float, y: float,
                    conductor: _section_model.ConductorSpec) -> None:
    """Draw one insulated conductor centred at ``(x, y)``: insulation disc
    (the OD), the stripe if it has one, then the conductor metal."""
    outer_radius = conductor.radius_mm
    metal_radius = conductor.conductor_radius_mm

    _disc(painter, x, y, outer_radius, conductor.insulation_rgb)

    if conductor.stripe_rgb is not None:
        wall = max(0.0, outer_radius - metal_radius)
        depth = wall * STRIPE_DEPTH_FRACTION
        path = _stripe_path(x, y, outer_radius, outer_radius - depth,
                            conductor.stripe_angle_deg, STRIPE_ARC_DEG)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(_color(conductor.stripe_rgb))
        painter.drawPath(path)

    _disc(painter, x, y, metal_radius, conductor.conductor_rgb)


@_check_types.do
def paint_cable(painter: QtGui.QPainter, cable: _section_model.CableSpec, angle_deg: float) -> None:
    """Draw a whole cable centred on the painter's origin, turned by
    *angle_deg*: jacket, shield, core fill, then every conductor in its place
    in the pack."""
    painter.save()
    painter.rotate(angle_deg)

    inner_radius = cable.core_radius_mm
    shield = cable.shield
    jacket = cable.jacket

    if jacket is not None:
        _disc(painter, 0.0, 0.0, cable.radius_mm, jacket.rgb)

    if shield is not None:
        shield_outer = inner_radius + shield.thickness_mm
        _disc(painter, 0.0, 0.0, shield_outer, shield.rgb)

        # a dotted ring through the shield, so it reads as a braid and not a solid tube
        braid = QtGui.QPen(QtGui.QColor(0, 0, 0, _BRAID_ALPHA))
        braid.setCosmetic(True)
        braid.setWidthF(1.0)
        braid.setStyle(QtCore.Qt.PenStyle.DotLine)
        painter.setPen(braid)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        middle = inner_radius + shield.thickness_mm / 2.0
        painter.drawEllipse(QtCore.QPointF(0.0, 0.0), middle, middle)

    if jacket is not None or shield is not None:
        _disc(painter, 0.0, 0.0, inner_radius, cable.core_rgb)

    for conductor, center in zip(cable.conductors, cable.conductor_centers_mm):
        paint_conductor(painter, center[0], center[1], conductor)

    painter.restore()
