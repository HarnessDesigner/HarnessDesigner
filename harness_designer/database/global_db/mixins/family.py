# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import family as _family  # NOQA


class FamilyMixin(BaseMixin):
    """Represent a family mixin in :mod:`harness_designer.database.global_db.mixins.family`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_family: "DefaultStoredValueType | _family.Family" = DefaultStoredValue

    @property
    def family(self) -> "_family.Family":
        """Return the family.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_family.Family`
        """
        if self._stored_family is DefaultStoredValue:
            from .. import family as _family  # NOQA

            family_id = self._table.select('family_id', id=self._db_id)
            self._stored_family = _family.Family(self._table.db.families_table, family_id[0][0])

        return self._stored_family

    _stored_family_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def family_id(self) -> int:
        """Return the family ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_family_id is DefaultStoredValue:
            self._stored_family_id = self._table.select('family_id', id=self._db_id)[0][0]

        return self._stored_family_id

    @family_id.setter
    def family_id(self, value: int):
        """Set the family ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_family_id = value
        self._stored_family = DefaultStoredValue

        self._table.update(self._db_id, family_id=value)
        self._populate('family_id')


class FamilyControl(_prop_ctrls.Category):
    """Represent a family control in :mod:`harness_designer.database.global_db.mixins.family`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`FamilyControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Family')

        self.choices: list[str] = []
        self.db_obj: FamilyMixin = None

        self.name_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Name')
        self.desc_ctrl = _prop_ctrls.LongStringProperty(self, 'Description')
        self.mfg_ctrl = _prop_ctrls.StringProperty(self, 'Manufacturer', read_only=True)

        self.addWidget(self.name_ctrl)
        self.addWidget(self.desc_ctrl)
        self.addWidget(self.mfg_ctrl)

        self.name_ctrl.propertyChanged.connect(self._on_name)
        self.desc_ctrl.propertyChanged.connect(self._on_desc)

    def set_obj(self, db_obj: FamilyMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`FamilyMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.name_ctrl.SetItems([])
            self.name_ctrl.SetValue('')
            self.mfg_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')
            self.name_ctrl.setEnabled(False)
            self.mfg_ctrl.setEnabled(False)
            self.desc_ctrl.setEnabled(False)
        else:
            family = db_obj.family
            mfg_id = family.manufacturer.db_id

            db_obj.table.execute(f'SELECT name FROM families WHERE mfg_id={mfg_id};')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(family.name)
            self.mfg_ctrl.SetValue(family.manufacturer.name)
            self.desc_ctrl.SetValue(family.description)
            self.name_ctrl.setEnabled(True)
            self.mfg_ctrl.setEnabled(True)
            self.desc_ctrl.setEnabled(True)

    def _on_name(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the name event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()
        mfg_id = self.db_obj.family.mfg_id

        self.db_obj.table.execute(f'SELECT id, description FROM families WHERE name="{name}" AND mfg_id={mfg_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.families_table.insert(name, mfg_id, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)

        self.db_obj.family_id = db_id

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        self.db_obj.family.description = desc
