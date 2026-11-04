# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_conductor as _wire_conductor


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
