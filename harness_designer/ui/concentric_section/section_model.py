# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Plain-data description of a bundle cross-section: what the concentric
cross-section widget draws.

Nothing here touches the database or Qt, so the layout code that works out
where each wire sits can build these objects headlessly. All lengths are
millimetres. The cross-section's origin is the bundle axis and +y points DOWN
(screen orientation).

One :class:`CableSpec` is one wire as the user sees it: a single insulated
conductor, a twisted group of conductors with no jacket, a jacketed
multi-conductor cable (with or without a shield), or a coax (one conductor
whose insulation is the dielectric, plus a shield and a jacket). A cable is
always moved as ONE unit: the conductors inside it keep their places relative
to the cable's centre.
"""

import math
import random

from . import packing as _packing
from ... import check_types as _check_types


# The default fill colour between a jacket / shield and the conductors inside it.
DEFAULT_CORE_RGB = (52, 52, 52)

# What each conductor metal looks like in section. Tinned and silver-plated
# copper look silvery, so the plating sets the colour; bare copper is copper.
_CONDUCTOR_RGB: dict[str, tuple[int, int, int]] = {
    'copper': (184, 115, 51),
    'tin': (176, 182, 188),
    'silver': (232, 232, 238),
    'nickel': (150, 154, 150),
    'gold': (214, 174, 56),
    'aluminum': (206, 210, 214),
}

_CONDUCTOR_SYMBOLS: dict[str, str] = {
    'cu': 'copper', 'sn': 'tin', 'ag': 'silver', 'ni': 'nickel', 'au': 'gold',
    'al': 'aluminum', 'aluminium': 'aluminum',
}


@_check_types.do
def conductor_rgb(material: str) -> tuple[int, int, int]:
    """Return the fill colour for a conductor material or plating name.

    A conductor is bare copper unless the name says otherwise, so a plating
    over copper ("tin", "silver plated copper", "Ni") picks the plating's
    colour and anything else is copper.

    :param material: The conductor's material / plating name or symbol.
    :type material: str
    :returns: ``(r, g, b)``.
    :rtype: tuple[int, int, int]
    """
    name = material.strip().lower()

    if name in _CONDUCTOR_SYMBOLS:
        return _CONDUCTOR_RGB[_CONDUCTOR_SYMBOLS[name]]

    for key in ('silver', 'tin', 'nickel', 'gold'):
        if key in name:
            return _CONDUCTOR_RGB[key]

    if 'alumin' in name:
        return _CONDUCTOR_RGB['aluminum']

    return _CONDUCTOR_RGB['copper']


@_check_types.do
def stripe_angle_for(key: str | bytes, index: int = 0) -> float:
    """Return where a stripe sits around a conductor, in degrees.

    "Random", but stable: seeded by the wire's key (and the conductor's
    index), so the same wire is drawn with its stripe in the same place every
    time instead of jumping on each repaint.

    :param key: The wire's key.
    :type key: str | bytes
    :param index: Which conductor of the cable.
    :type index: int
    :returns: An angle in ``[0, 360)``.
    :rtype: float
    """
    return random.Random(repr((key, index))).uniform(0.0, 360.0)


@_check_types.do
def helix_length_mm(run_length_mm: float, helix_radius_mm: float, lay_length_mm: float) -> float:
    """Return the length of a wire that follows a helix around the bundle
    axis for *run_length_mm* of bundle.

    The same helix formula the wire service loop uses (``sqrt((2 pi R turns)
    ** 2 + height ** 2)``), with ``turns = run / lay length`` and R the
    distance of the wire's centre from the axis. A lay length of 0 means the
    wire is not twisted (a straight core wire), so it is just the run.

    :param run_length_mm: The straight length of bundle the wire runs through.
    :type run_length_mm: float
    :param helix_radius_mm: The wire centre's distance from the bundle axis.
    :type helix_radius_mm: float
    :param lay_length_mm: The layer's lay length (one full turn), or 0.0.
    :type lay_length_mm: float
    :returns: The wire's length, in mm.
    :rtype: float
    """
    if lay_length_mm <= 0.0:
        return run_length_mm

    turns = run_length_mm / lay_length_mm
    around = 2.0 * math.pi * helix_radius_mm * turns
    return math.sqrt(around * around + run_length_mm * run_length_mm)


class ConductorSpec:
    """One insulated conductor, drawn like a single-conductor wire: the
    insulation disc (``od_mm`` across, the primary colour), an optional stripe
    cross-section on it, and the conductor disc (``conductor_dia_mm`` across,
    the metal's colour) in the middle.
    """

    @_check_types.do
    def __init__(self, conductor_dia_mm: float, od_mm: float, conductor_rgb: tuple[int, int, int],
                 insulation_rgb: tuple[int, int, int], stripe_rgb: tuple[int, int, int] | None = None,
                 stripe_angle_deg: float = 0.0):
        self.conductor_dia_mm = conductor_dia_mm
        self.od_mm = od_mm
        self.conductor_rgb = conductor_rgb
        self.insulation_rgb = insulation_rgb
        self.stripe_rgb = stripe_rgb
        self.stripe_angle_deg = stripe_angle_deg

    @property
    @_check_types.do
    def radius_mm(self) -> float:
        """The insulation's outer radius."""
        return self.od_mm / 2.0

    @property
    @_check_types.do
    def conductor_radius_mm(self) -> float:
        """The metal conductor's radius."""
        return self.conductor_dia_mm / 2.0


class ShieldSpec:
    """A shield (braid or foil) ring around the conductors."""

    @_check_types.do
    def __init__(self, thickness_mm: float, rgb: tuple[int, int, int] = (190, 192, 196)):
        self.thickness_mm = thickness_mm
        self.rgb = rgb


class JacketSpec:
    """An outer jacket (the outer insulation of a coax) around everything."""

    @_check_types.do
    def __init__(self, thickness_mm: float, rgb: tuple[int, int, int] = (30, 30, 30)):
        self.thickness_mm = thickness_mm
        self.rgb = rgb


class CableSpec:
    """One wire, moved as a unit. Built from its conductors plus an optional
    shield and an optional jacket (see the module docstring for the four
    shapes); the conductors are packed as tightly as possible inside as near
    a circle as possible (:func:`.packing.pack_circles`).
    """

    @_check_types.do
    def __init__(self, key: str | bytes, conductors: list[ConductorSpec] | tuple[ConductorSpec, ...],
                 shield: ShieldSpec | None = None, jacket: JacketSpec | None = None,
                 core_rgb: tuple[int, int, int] = DEFAULT_CORE_RGB):
        self.key = key
        self.conductors = tuple(conductors)
        self.shield = shield
        self.jacket = jacket
        self.core_rgb = core_rgb

        radii = tuple([conductor.radius_mm for conductor in self.conductors])
        centers, core_radius = _packing.pack_circles(radii)

        self._centers = centers
        self._core_radius_mm = core_radius

        radius = core_radius
        if shield is not None:
            radius += shield.thickness_mm

        if jacket is not None:
            radius += jacket.thickness_mm

        self._radius_mm = radius

    @classmethod
    @_check_types.do
    def fit_to_od(cls, key: str | bytes, count: int, od_mm: float, conductor_dia_mm: float,
                  conductor_rgb: tuple[int, int, int], insulation_rgb: tuple[int, int, int],
                  stripe_rgb: tuple[int, int, int] | None = None, shield: ShieldSpec | None = None,
                  jacket: JacketSpec | None = None) -> "CableSpec":
        """Build a cable of *count* identical conductors that is *od_mm*
        across overall: the conductors are sized to fill what is left inside
        the shield and jacket. With one conductor and neither, that conductor
        simply IS *od_mm* across (the single-wire rule).

        :param key: The wire's key.
        :param count: Number of conductors.
        :param od_mm: The cable's overall outside diameter.
        :param conductor_dia_mm: Each metal conductor's diameter.
        :param conductor_rgb: The metal's colour.
        :param insulation_rgb: The insulation's (primary) colour.
        :param stripe_rgb: The stripe colour, or ``None``.
        :param shield: The shield, or ``None``.
        :param jacket: The jacket, or ``None``.
        :returns: The cable.
        :rtype: :class:`CableSpec`
        """
        inside = od_mm / 2.0
        if shield is not None:
            inside -= shield.thickness_mm

        if jacket is not None:
            inside -= jacket.thickness_mm

        factor = _packing.pack_circles(tuple([1.0] * count))[1]
        conductor_od = 2.0 * inside / factor

        conductors = []
        for index in range(count):
            angle = 0.0
            if stripe_rgb is not None:
                angle = stripe_angle_for(key, index)

            conductors.append(ConductorSpec(
                conductor_dia_mm, conductor_od, conductor_rgb, insulation_rgb, stripe_rgb, angle))

        return cls(key, conductors, shield, jacket)

    @property
    @_check_types.do
    def conductor_centers_mm(self) -> tuple[tuple[float, float], ...]:
        """Each conductor's centre, relative to the cable's centre."""
        return self._centers

    @property
    @_check_types.do
    def core_radius_mm(self) -> float:
        """The radius of the circle that holds every conductor."""
        return self._core_radius_mm

    @property
    @_check_types.do
    def radius_mm(self) -> float:
        """The cable's overall outside radius (jacket included)."""
        return self._radius_mm

    @property
    @_check_types.do
    def od_mm(self) -> float:
        """The cable's overall outside diameter."""
        return self._radius_mm * 2.0


class PlacedCable:
    """A cable at a place in the cross-section. ``lay_length_mm`` is the lay
    length of the layer it sits in (0.0 for an untwisted core wire)."""

    @_check_types.do
    def __init__(self, cable: CableSpec, x_mm: float, y_mm: float, angle_deg: float = 0.0,
                 lay_length_mm: float = 0.0):
        self.cable = cable
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.angle_deg = angle_deg
        self.lay_length_mm = lay_length_mm

    @property
    @_check_types.do
    def axis_distance_mm(self) -> float:
        """The cable centre's distance from the bundle axis -- the helix
        radius of the wire."""
        return math.hypot(self.x_mm, self.y_mm)

    @_check_types.do
    def contains(self, x_mm: float, y_mm: float) -> bool:
        """Whether the point is inside the cable's overall outline."""
        return math.hypot(x_mm - self.x_mm, y_mm - self.y_mm) <= self.cable.radius_mm


class SectionSpec:
    """Everything the cross-section view draws: the placed cables, the
    bundle's outline, guide rings for the layers, and the length of bundle the
    section stands for (what the helix length of a wire is worked from)."""

    @_check_types.do
    def __init__(self, cables: list[PlacedCable] | None = None, envelope_dia_mm: float = 0.0,
                 layer_dia_mm: list[float] | None = None, run_length_mm: float = 0.0):
        self.cables: list[PlacedCable] = []
        if cables is not None:
            self.cables = cables

        self.envelope_dia_mm = envelope_dia_mm

        self.layer_dia_mm: list[float] = []
        if layer_dia_mm is not None:
            self.layer_dia_mm = layer_dia_mm

        self.run_length_mm = run_length_mm

    @_check_types.do
    def content_radius_mm(self) -> float:
        """The radius, about the bundle axis, that holds everything drawn."""
        radius = self.envelope_dia_mm / 2.0
        for placed in self.cables:
            radius = max(radius, placed.axis_distance_mm + placed.cable.radius_mm)

        return radius

    @_check_types.do
    def find(self, key: str | bytes) -> PlacedCable:
        """Return the placed cable with this key.

        :raises KeyError: When there is none.
        """
        for placed in self.cables:
            if placed.cable.key == key:
                return placed

        raise KeyError(key)

    @_check_types.do
    def hit_test(self, x_mm: float, y_mm: float) -> PlacedCable | None:
        """Return the topmost cable under the point (the last one drawn), or
        ``None`` over empty space."""
        for placed in reversed(self.cables):
            if placed.contains(x_mm, y_mm):
                return placed

        return None


class WireDetail:
    """What the information panel shows about one wire. Everything is already
    a display value; the current and the temperature are what the circuit
    solver found (``None`` when the wire is in no solved circuit)."""

    @_check_types.do
    def __init__(self, name: str = '', part_number: str = '', color: str = '', stripe_color: str = '',
                 size: str = '', conductor_material: str = '', insulation: str = '', conductors: int = 1,
                 shielded: bool = False, layer: str = '', lay_direction: str = '',
                 current_a: float | None = None, max_temp_c: float | None = None,
                 over_temp: bool = False, runaway: bool = False):
        self.name = name
        self.part_number = part_number
        self.color = color
        self.stripe_color = stripe_color
        self.size = size
        self.conductor_material = conductor_material
        self.insulation = insulation
        self.conductors = conductors
        self.shielded = shielded
        self.layer = layer
        self.lay_direction = lay_direction
        self.current_a = current_a
        self.max_temp_c = max_temp_c
        self.over_temp = over_temp
        self.runaway = runaway
