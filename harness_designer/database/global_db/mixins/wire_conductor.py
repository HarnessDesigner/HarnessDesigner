# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from .base import BaseMixin
from ... import id_generator as _id_generator
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_conductor as _wire_conductor
    from .... import color as _color


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

        That is a wire with a twist rate (``tpi`` above 0), two or three conductors, no outer jacket (its colour is "no
        colour") and a ``wire_conductors`` row for each conductor. Any other multi-conductor wire is drawn as a plain tube.

        :rtype: bool
        """
        if self.tpi <= 0.0:
            return False

        if self.num_conductors not in (2, 3):
            return False

        if self.color_id != _id_generator.NO_COLOR_UUID.bytes:
            return False

        return len(self.conductors) == self.num_conductors

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
