from typing import TYPE_CHECKING

from .base import BaseMixin

if TYPE_CHECKING:
    from .. import resource as _resource


class OverlayMixin(BaseMixin):

    @property
    def overlay(self) -> "_resource.Resource":
        from ..resource import Resource

        image_id = self._table.select('overlay_id', id=self._db_id)
        return Resource(self._table.db.resources_table, image_id[0])

    @overlay.setter
    def overlay(self, value: "_resource.Resource"):
        self._table.update(self._db_id, overlay_id=value.db_id)

    @property
    def overlay_id(self) -> int:
        return self._table.select('overlay_id', id=self._db_id)[0][0]

    @overlay_id.setter
    def overlay_id(self, value: int):
        self._table.update(self._db_id, overlay_id=value)


