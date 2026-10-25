# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import derating as _derating


class DeratingMixin(BaseMixin):
    """The manufacturer's derating table of a terminal, a wire or a splice.

    The table is cached by the ``deratings`` table class, not by the part:
    the terminals, wires and splices tables call :meth:`load_deratings` from
    their ``__getitem__`` as they load a part, which reads the part's whole
    table in one query, and :attr:`deratings` then serves it from memory.
    """

    @_check_types.do
    def load_deratings(self) -> None:
        """Have the ``deratings`` table read this part's whole derating table now.

        Does nothing while the database is still starting up and the
        ``deratings`` table does not exist yet; :attr:`deratings` reads it
        on the first ask instead.
        """
        try:
            deratings_table = self._table.db.deratings_table
        except AttributeError:
            return

        deratings_table.for_part(self._table.__table_name__, self._db_id)

    @_check_types.do
    def reload_deratings(self) -> None:
        """Read the part's derating table again, for rows added or removed behind the cache's back."""
        deratings_table = self._table.db.deratings_table

        deratings_table.forget(self._db_id)
        deratings_table.for_part(self._table.__table_name__, self._db_id)

    @property
    @_check_types.do
    def deratings(self) -> tuple["_derating.Derating", ...]:
        """The part's derating table, first row first; empty when the
        manufacturer gave none.

        :rtype: tuple[_derating.Derating, ...]
        """
        return self._table.db.deratings_table.for_part(self._table.__table_name__, self._db_id)
