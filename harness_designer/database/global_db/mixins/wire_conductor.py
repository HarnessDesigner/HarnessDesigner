# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import enum

from .base import BaseMixin
from ... import id_generator as _id_generator
from ....shapes import twisted_wire as _twisted_wire
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_conductor as _wire_conductor
    from .... import color as _color


class CableStyle(enum.Enum):
    """How a catalog wire is placed and drawn (TWISTED_WIRE_DESIGN.md, section 8a). Worked out from the part, never stored.

    A wire is a CABLE when it is shielded or has more than one conductor; a coax that is not shielded stays a wire.
    """

    WIRE = 0
    """Not a cable: placed as a ``pjt_wires`` wire."""

    TWISTED = 1
    """A twisted pair or triple with no jacket (:attr:`WireConductorMixin.is_twisted`)."""

    RIBBON = 2
    """Discrete ribbon cable: conductors side by side, no single jacket round them, not twisted."""

    JACKETED = 3
    """Every other cable (shielded, coax, round multi-conductor): drawn as one tube."""


class WireConductorMixin(BaseMixin):
    """The individual conductors inside a multi-conductor wire.

    The conductors are cached by the ``wire_conductors`` table class, not by the wire: the wires table calls
    :meth:`load_conductors` from its ``__getitem__`` as it loads a wire, which reads the wire's whole set of
    conductors in one query, and :attr:`conductors` then serves them from memory.
    """

    @_check_types.do
    def load_conductors(self) -> None:
        """Have the ``wire_conductors`` table read this wire's conductors now.

        Does nothing while the database is still starting up and the ``wire_conductors`` table does not exist yet;
        :attr:`conductors` reads them on the first ask instead.
        """
        try:
            conductors_table = self._table.db.wire_conductors_table
        except AttributeError:
            return

        conductors_table.for_wire(self._db_id)

    @_check_types.do
    def reload_conductors(self) -> None:
        """Read the wire's conductors again, for rows added or removed behind the cache's back."""
        conductors_table = self._table.db.wire_conductors_table

        conductors_table.forget(self._db_id)
        conductors_table.for_wire(self._db_id)

    @property
    @_check_types.do
    def conductors(self) -> tuple["_wire_conductor.WireConductor", ...]:
        """The conductors inside the wire, first conductor first; empty for a wire that is a single conductor.

        :rtype: tuple[_wire_conductor.WireConductor, ...]
        """
        return self._table.db.wire_conductors_table.for_wire(self._db_id)

    @property
    @_check_types.do
    def is_twisted(self) -> bool:
        """Whether the wire is drawn as a twisted pair or triple (TWISTED_WIRE_DESIGN.md, sections 1 and 2a).

        That is a wire with a twist rate (``tpi`` above 0), two or more conductors (any number: user, 2026-11-05), no outer
        jacket (its colour is "no colour") and a ``wire_conductors`` row for each conductor. Any other multi-conductor wire is
        drawn as a plain tube.

        :rtype: bool
        """
        if self.tpi <= 0.0:
            return False

        if self.num_conductors < 2:
            return False

        if self.color_id != _id_generator.NO_COLOR_UUID.bytes:
            return False

        return len(self.conductors) == self.num_conductors

    @property
    @_check_types.do
    def is_cable(self) -> bool:
        """Whether a placed copy of this wire is a cable (``pjt_cables``) rather than a wire (``pjt_wires``): the wire is
        shielded, whatever its conductor count, or has more than one conductor.

        :rtype: bool
        """
        return bool(self.shielded) or self.num_conductors > 1

    @property
    @_check_types.do
    def cable_style(self) -> CableStyle:
        """How the wire is drawn as a cable; :attr:`CableStyle.WIRE` for a wire that is not a cable.

        The style cannot come from ``wire_type`` alone (TE leaves it empty on nearly every part): a twisted cable is told
        by its twist rate, jacket and conductors, a ribbon by its wire type.

        :rtype: CableStyle
        """
        if not self.is_cable:
            return CableStyle.WIRE

        if self.is_twisted:
            return CableStyle.TWISTED

        if self.wire_type.name == 'Ribbon':
            return CableStyle.RIBBON

        return CableStyle.JACKETED

    @property
    @_check_types.do
    def is_ribbon(self) -> bool:
        """Whether the wire is drawn as a ribbon cable (:attr:`CableStyle.RIBBON`).

        :rtype: bool
        """
        return self.cable_style is CableStyle.RIBBON

    @property
    @_check_types.do
    def ribbon_pitch_mm(self) -> float:
        """The centreline pitch a ribbon cable of this part is drawn with: the catalogue gives none, so it is the smallest
        standard pitch that holds one insulated conductor (the first conductor's ``od_mm`` when it has one, else its size and
        ``shapes.twisted_wire.INSULATION_MM``).

        :rtype: float
        """
        conductors = self.conductors
        od = conductors[0].stored_od_mm if conductors else 0.0

        return _twisted_wire.ribbon_pitch(self.conductor_dia_mm or 0.0, od or 0.0)

    @property
    @_check_types.do
    def trunk_size(self) -> tuple[float, float]:
        """How wide and how thick the cable is drawn, mm: a ribbon is ``count * pitch`` by one pitch; any other cable is round
        at its ``od_mm``, or, when the catalogue gives none, at the diameter that holds its conductors
        (``shapes.twisted_wire.jacket_diameter``).

        :rtype: tuple[float, float]
        """
        count = len(self.conductors) or max(1, self.num_conductors)

        if self.is_ribbon:
            pitch = self.ribbon_pitch_mm
            return count * pitch, pitch

        od = self.od_mm

        if not od:
            conductors = self.conductors
            insulated = _twisted_wire.insulated_diameter(
                self.conductor_dia_mm or 0.0, (conductors[0].stored_od_mm or 0.0) if conductors else 0.0)
            od = _twisted_wire.jacket_diameter(count, insulated)

        return od, od

    @property
    @_check_types.do
    def conductor_colors(self) -> tuple[tuple["_color.Color", _Union["_color.Color", None]], ...]:
        """The colours of the conductors, first conductor first: ``(insulation colour, stripe colour)`` each, the stripe
        colour ``None`` for a conductor without a stripe.

        :rtype: tuple[tuple[_color.Color, _color.Color | None], ...]
        """
        colors_table = self._table.db.colors_table
        result = []

        for conductor in self.conductors:
            color = colors_table[conductor.color_id]

            if conductor.has_stripe:
                stripe = colors_table[conductor.stripe_color_id]
            else:
                stripe = None

            result.append((color, stripe))

        return tuple(result)
