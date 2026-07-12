# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import adhesive as _adhesive  # NOQA


class AdhesiveMixin(BaseMixin):
    """Represent an adhesive mixin in :mod:`harness_designer.database.global_db.mixins.adhesive`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_adhesives: list["_adhesive.Adhesive"] | DefaultStoredValueType = DefaultStoredValue

    @property
    def adhesives(self) -> list["_adhesive.Adhesive"]:
        """Return the adhesives.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_adhesive.Adhesive']
        """
        if self._stored_adhesives is DefaultStoredValue:
            ids = self.adhesive_ids

            if not ids:
                self._stored_adhesives = []
            else:
                from .. import adhesive as _adhesive_module

                adhesives_table = self._table.db.adhesives_table
                placeholders = ', '.join('?' * len(ids))
                adhesives_table.execute(
                    f'SELECT id FROM adhesives WHERE id IN ({placeholders});', ids)
                found_ids = {row[0] for row in adhesives_table.fetchall()}

                self._stored_adhesives = [
                    _adhesive_module.Adhesive(adhesives_table, db_id)
                    for db_id in ids if db_id in found_ids
                ]

        return list(self._stored_adhesives)

    _stored_adhesive_ids: list | DefaultStoredValueType = DefaultStoredValue

    @property
    def adhesive_ids(self) -> list[str]:
        """Return the adhesive IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        if self._stored_adhesive_ids is DefaultStoredValue:
            value = self._table.select('adhesive_ids', id=self._db_id)[0][0]
            self._stored_adhesive_ids = eval(value)

        return list(self._stored_adhesive_ids)

    @adhesive_ids.setter
    def adhesive_ids(self, value: list[str]):
        """Set the adhesive IDs.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        self._stored_adhesive_ids = value
        self._stored_adhesives = DefaultStoredValue
        self._table.update(self._db_id, adhesive_ids=str(value))
        self._populate('adhesive_ids')


class AdhesiveControl(_prop_ctrls.ArrayStringProperty):
    """Represent an adhesive control in :mod:`harness_designer.database.global_db.mixins.adhesive`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`AdhesiveControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: AdhesiveMixin = None

        super().__init__(parent, 'Adhesives')

    def _on_adhesives(self, evt):
        """Handle the adhesives event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.adhesive_ids = value

    def set_obj(self, db_obj: AdhesiveMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`AdhesiveMixin`
        """
        self.db_obj = db_obj
        self.SetValue(db_obj.adhesive_ids)
