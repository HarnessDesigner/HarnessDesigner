# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import uuid

from typing import Iterable as _Iterable, TYPE_CHECKING

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import DescriptionMixin
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import color as _color


# Plating symbol prefix -> named-color lookup key (this same db's own
# colors_table). Mirrors the finish colors a plated conductor/terminal
# actually looks like under this app's material rendering (Sn/Tin,
# Cu/Copper, ...).
_PLATING_PREFIX_COLOR_NAMES = (
    ('Sn', 'Tin'),
    ('Cu', 'Copper'),
    ('Al', 'Aluminum'),
    ('Ti', 'Titanium'),
    ('Zn', 'Zinc'),
    ('Au', 'Gold'),
    ('Ag', 'Silver'),
    ('Ni', 'Nickel'),
)

_DEFAULT_PLATING_COLOR_NAME = 'Tin'


class PlatingsTable(TableBase):
    """Represent a platings table in :mod:`harness_designer.database.global_db.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'platings'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import platings

        return platings.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import platings

        platings.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        platings.add_records(self._con, splash, data_path)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import platings

        platings.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["Plating"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Plating']
        """

        for db_id in TableBase.__iter__(self):
            yield Plating(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "Plating":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Plating`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes, uuid.UUID)):
            if item in self:
                return Plating(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', symbol=item)
        if db_id:
            return Plating(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, symbol: str, description: str) -> "Plating":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param symbol: Value for ``symbol``.
        :type symbol: str
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Plating`
        """
        db_id = TableBase.insert(self, symbol=symbol, description=description)
        return Plating(self, db_id)

    @property
    @_check_types.do
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT symbol FROM {self.__table_name__};')]


class Plating(EntryBase, DescriptionMixin):
    """Represent a plating in :mod:`harness_designer.database.global_db.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PlatingsTable = None

    _stored_symbol: DefaultStoredValueType | str = DefaultStoredValue

    @property
    @_check_types.do
    def symbol(self) -> str:
        """Return the symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_symbol is DefaultStoredValue:
            self._stored_symbol = self._table.select('symbol', id=self._db_id)[0][0]

        return self._stored_symbol

    @symbol.setter
    @_check_types.do
    def symbol(self, value: str):
        """Set the symbol.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_symbol = value

        self._table.update(self._db_id, symbol=value)
        self._populate('symbol')

    @property
    @_check_types.do
    def color_name(self) -> str:
        """Return the ``colors_table`` lookup name that visually
        represents this plating (e.g. ``'Sn60/Pb40'`` -> ``'Tin'``).

        :returns: The matching color name, or
            :data:`_DEFAULT_PLATING_COLOR_NAME` if :attr:`symbol` doesn't
            start with any known prefix.
        :rtype: str
        """
        symbol = self.symbol
        for prefix, name in _PLATING_PREFIX_COLOR_NAMES:
            if symbol.startswith(prefix):
                return name

        return _DEFAULT_PLATING_COLOR_NAME

    @property
    @_check_types.do
    def color(self) -> "_color.Color":
        """Return the actual :class:`~harness_designer.database.global_db.color.Color`
        that visually represents this plating (see :attr:`color_name`).

        :returns: Property value.
        :rtype: :class:`~harness_designer.database.global_db.color.Color`
        """
        return self._table.db.colors_table[self.color_name]
