# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import gender as _gender  # NOQA


class GenderMixin(BaseMixin):
    """Represent a gender mixin in :mod:`harness_designer.database.global_db.mixins.gender`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_gender: "DefaultStoredValueType | _gender.Gender" = DefaultStoredValue

    @property
    def gender(self) -> "_gender.Gender":
        """Return the gender.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_gender.Gender`
        """
        if self._stored_gender is DefaultStoredValue:
            from .. import gender as _gender  # NOQA

            gender_id = self._table.select('gender_id', id=self._db_id)
            self._stored_gender = _gender.Gender(self._table.db.genders_table, gender_id[0][0])

        return self._stored_gender

    _stored_gender_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def gender_id(self) -> int:
        """Return the gender ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_gender_id is DefaultStoredValue:
            self._stored_gender_id = self._table.select('gender_id', id=self._db_id)[0][0]

        return self._stored_gender_id

    @gender_id.setter
    def gender_id(self, value: int):
        """Set the gender ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_gender_id = value
        self._stored_gender = DefaultStoredValue

        self._table.update(self._db_id, gender_id=value)
        self._populate('gender_id')


class GenderControl(_prop_ctrls.ComboBoxProperty):
    """Represent a gender control in :mod:`harness_designer.database.global_db.mixins.gender`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`GenderControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        self.choices: list[str] = []
        self.db_obj: GenderMixin = None

        super().__init__(parent, 'Gender')
        self.propertyChanged.connect(self._on_gender)

    def set_obj(self, db_obj: GenderMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`GenderMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems(self.choices)
            self.SetValue('')
            self.setEnabled(False)
        else:
            db_obj.table.execute('SELECT name FROM genders;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.gender.name)
            self.setEnabled(True)

    def _on_gender(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the gender event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM genders WHERE name=?;', (name,))
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.genders_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.gender_id = db_id
