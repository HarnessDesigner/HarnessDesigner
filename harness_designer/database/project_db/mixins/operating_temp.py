# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import re

from .base import BaseMixin
from .. import circuit_solver as _circuit_solver
from .... import check_types as _check_types


# The first number in a rated-temperature name such as "+105 °C" or "-40°C".
_CELSIUS = re.compile(r'[+-]?\d+(?:\.\d+)?')


class OperatingTempMixin(BaseMixin):
    """The temperature a part works in, how hot it runs, and whether that is
    more than it is rated for. For project rows that carry heat: wires, wire
    service loops, splices and terminals.

    The row class needs ``part`` (its catalog part, with a rated maximum
    temperature), ``resistance`` (ohms at 20 degrees Celsius), ``circuit_id``
    and, for :class:`WireOperatingTempMixin`, ``length_mm`` and
    ``_resistance_over(length_mm)`` (the resistance over a length already known).

    :meth:`part_data` is the one function the circuit solver calls to learn
    about a part. Where the manufacturer's derating table for the part is in
    the global database (``part.deratings``, loaded with the part) it takes the
    thermal resistance from that table; otherwise it calculates it.
    """

    @property
    @_check_types.do
    def operating_temp(self) -> float | None:
        """The temperature the part works in, in degrees Celsius, as the user
        (or a connected part) set it. ``None`` means nobody has set one.

        :rtype: float | None
        """
        return self._table.select('operating_temp', id=self._db_id)[0][0]

    @operating_temp.setter
    @_check_types.do
    def operating_temp(self, value: float | None) -> None:
        """Set the temperature the part works in. ``None`` clears it.

        :param value: Degrees Celsius, or ``None``.
        :type value: float | None
        """
        self._table.update(self._db_id, operating_temp=value)
        self._populate('operating_temp')

    @property
    @_check_types.do
    def ambient_c(self) -> float:
        """The temperature around the part: :attr:`operating_temp`, or
        :data:`circuit_solver.DEFAULT_AMBIENT_C` while nobody has set one.

        :rtype: float
        """
        value = self.operating_temp

        if value is None:
            return _circuit_solver.DEFAULT_AMBIENT_C

        return value

    @property
    @_check_types.do
    def max_temp_c(self) -> float | None:
        """The hottest the part is rated for, in degrees Celsius, read from its
        catalog part. ``None`` when the part has no rating ("Unknown").

        :rtype: float | None
        """
        temperature = self.part.max_temp

        if temperature is None:
            return None

        found = _CELSIUS.search(temperature.name)

        if found is None:
            return None

        return float(found.group(0))

    @_check_types.do
    def _thermal_resistance(self) -> float:
        """The part's thermal resistance to the air around it, in K/W.
        A terminal or splice has nothing in the database to derive it from, so
        it is an assumed constant.

        :rtype: float
        """
        return _circuit_solver.CONTACT_THERMAL_RESISTANCE

    @_check_types.do
    def _rated_amps(self) -> float | None:
        """The part's own rated current, in amps: what a manufacturer's
        derating *factor* scales. ``None`` unless the row class knows it (a
        terminal's catalog part has one; a wire's and a splice's do not).

        :rtype: float | None
        """
        return None

    @_check_types.do
    def _derating_limits(self) -> list[tuple[float, float]]:
        """The manufacturer's derating table for this part, as the ``(ambient
        in degrees Celsius, the most amps at it)`` pairs :func:`_circuit_solver.calibrate_theta`
        reads. Only ambient rows count (a row with a conductor count is a
        bundling row); a row gives ``max_amps``, or ``derating_factor`` times
        the part's rated current (skipped when the part has none).

        :returns: The pairs; empty when the manufacturer gave no table.
        :rtype: list[tuple[float, float]]
        """
        rated_amps = self._rated_amps()
        limits = []

        for row in self.part.deratings:
            if row.ambient_temp_c is None or row.conductor_count is not None:
                continue

            amps = row.max_amps

            if amps is None and row.derating_factor is not None and rated_amps is not None:
                amps = row.derating_factor * rated_amps

            if amps is not None:
                limits.append((float(row.ambient_temp_c), float(amps)))

        return limits

    @_check_types.do
    def _bundling_rows(self) -> tuple[tuple[int, float], ...]:
        """The manufacturer's bundling table for this part: ``(number of
        current-carrying conductors bundled together, factor on the current the
        part may carry)`` from its rows that have a ``conductor_count`` and a
        ``derating_factor``. A bundling row that gives only ``max_amps`` is not
        used: without the part's own rated current there is nothing to make a
        factor of it.

        :returns: The rows by conductor count; empty when the manufacturer gave none.
        :rtype: tuple[tuple[int, float], ...]
        """
        return tuple(sorted((row.conductor_count, float(row.derating_factor)) for row in self.part.deratings
                            if row.conductor_count is not None and row.derating_factor is not None))

    @_check_types.do
    def _part_data(self, resistance: float, thermal_resistance: float,
                   length_m: float = 0.0) -> "_circuit_solver.PartData":
        """Put what :meth:`part_data` has worked out together with the rest of
        what the solver is told about the part. This is where the manufacturer's
        derating table is used: when the part has one that can say, its thermal
        resistance replaces the calculated one, and its bundling rows go to the
        solver to use when the part is in a bundle.

        :param resistance: The resistance at 20 degrees Celsius, in ohms.
        :type resistance: float
        :param thermal_resistance: The calculated thermal resistance to the air, in K/W.
        :type thermal_resistance: float
        :param length_m: The length of the run in metres, for a wire; what the
            heat per metre of a bundle is worked out from.
        :type length_m: float
        :rtype: :class:`_circuit_solver.PartData`
        """
        r20 = float(resistance or 0.0)
        ambient_c = self.ambient_c
        rated_max_c = self.max_temp_c

        from_table = _circuit_solver.calibrate_theta(
            self._derating_limits(), r20, _circuit_solver.COPPER_ALPHA, rated_max_c, ambient_c)

        return _circuit_solver.PartData(
            r20=r20,
            alpha=_circuit_solver.COPPER_ALPHA,
            theta=thermal_resistance if from_table is None else from_table,
            ambient_c=ambient_c,
            rated_max_c=rated_max_c,
            length_m=length_m,
            bundling=self._bundling_rows())

    @_check_types.do
    def part_data(self) -> "_circuit_solver.PartData":
        """Collect what the circuit solver needs to know about this part.

        :returns: Its resistance at 20 degrees Celsius (0.0 where the part has
            no data), temperature coefficient, thermal resistance, ambient
            temperature and rated maximum.
        :rtype: :class:`_circuit_solver.PartData`
        """
        return self._part_data(self.resistance, self._thermal_resistance())

    @property
    @_check_types.do
    def temperature_c(self) -> float:
        """How hot the part runs: its ambient plus its own rise at the current
        its circuit puts through it. Just the ambient when it is in no circuit.

        :rtype: float
        """
        circuit_id = self.circuit_id

        if circuit_id is None:
            return self.ambient_c

        return self._table.db.pjt_circuits_table[circuit_id].temperature_at(self)

    @property
    @_check_types.do
    def over_temperature(self) -> bool:
        """Whether the part runs hotter than it is rated for. A part with no
        rating is never over temperature.

        :rtype: bool
        """
        rated = self.max_temp_c

        if rated is None:
            return False

        return self.temperature_c > rated


class WireOperatingTempMixin(OperatingTempMixin):
    """:class:`OperatingTempMixin` for a wire or a wire service loop, whose
    thermal resistance comes from the wire's outer surface."""

    @_check_types.do
    def _thermal_resistance(self, length_mm: float | None = None) -> float:
        """The wire's thermal resistance to the air, in K/W, from its outside
        diameter and its routed length (0.0 when either is unknown).

        :param length_mm: The length, when the caller already has it. Working
            it out can mean walking the wire's whole route, so it is only
            looked up here when it is not given.
        :type length_mm: float | None
        :rtype: float
        """
        if length_mm is None:
            length_mm = self.length_mm

        return _circuit_solver.wire_theta(
            float(self.part.od_mm or 0.0), float(length_mm))

    @_check_types.do
    def part_data(self) -> "_circuit_solver.PartData":
        """:meth:`OperatingTempMixin.part_data` with the length worked out once:
        the resistance and the thermal resistance both depend on it, and for a
        routed wire it is the costly part.

        :rtype: :class:`_circuit_solver.PartData`
        """
        length_mm = float(self.length_mm)

        return self._part_data(self._resistance_over(length_mm), self._thermal_resistance(length_mm),
                               length_mm / 1000.0)
