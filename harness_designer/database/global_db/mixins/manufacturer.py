from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import manufacturer as _manufacturer  # NOQA


class ManufacturerMixin(BaseMixin):

    @property
    def manufacturer(self) -> "_manufacturer.Manufacturer":
        from .. import manufacturer as _manufacturer  # NOQA

        mfg_id = self._table.select('mfg_id', id=self._db_id)
        return _manufacturer.Manufacturer(self._table.db.manufacturers_table, mfg_id[0][0])

    @manufacturer.setter
    def manufacturer(self, value: "_manufacturer.Manufacturer"):
        self._table.update(self._db_id, mfg_id=value.db_id)

    @property
    def mfg_id(self) -> int:
        return self._table.select('mfg_id', id=self._db_id)[0][0]

    @mfg_id.setter
    def mfg_id(self, value: int):
        self._table.update(self._db_id, mfg_id=value)
