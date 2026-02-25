from .base import BaseMixin


class ProtectionMixin(BaseMixin):

    @property
    def protections(self) -> list[str]:
        res = []

        protection_ids = eval(self._table.select('protection_ids', id=self._db_id)[0][0])
        for protection_id in protection_ids:
            res.append(self._table.db.protections_table[protection_id].name)

        return res

    @protections.setter
    def protections(self, value: list[str]):
        protection_ids = []

        for name in value:
            try:
                protection_ids.append(self._table.db.protections_table[name].db_id)
            except KeyError:
                pass

        self._table.update(self._db_id, protection_ids=str(protection_ids))
