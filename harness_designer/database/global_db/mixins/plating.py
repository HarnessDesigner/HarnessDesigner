# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import plating as _plating


class PlatingMixin(BaseMixin):
    """Represent a plating mixin in :mod:`harness_designer.database.global_db.mixins.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_plating: "DefaultStoredValueType | _plating.Plating" = DefaultStoredValue

    @property
    def plating(self) -> "_plating.Plating":
        """Return the plating.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_plating.Plating`
        """
        if self._stored_plating is DefaultStoredValue:
            self._stored_plating = self._table.db.platings_table[self.plating_id]

        return self._stored_plating

    _stored_plating_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def plating_id(self) -> int:
        """Return the plating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_plating_id is DefaultStoredValue:
            self._stored_plating_id = self._table.select('plating_id', id=self._db_id)[0][0]

        return self._stored_plating_id

    @plating_id.setter
    def plating_id(self, value: int):
        """Set the plating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_plating_id = value
        self._stored_plating = DefaultStoredValue
        self._table.update(self._db_id, plating_id=value)
        self._populate('plating_id')


class PlatingControl(_prop_ctrls.Category):
    """Represent a plating control in :mod:`harness_designer.database.global_db.mixins.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`PlatingControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Plating')

        self.attribute_name = 'plating'

        self.choices: list[str] = []
        self.db_obj: PlatingMixin = None

        self.symbol_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Symbol')
        self.desc_ctrl = _prop_ctrls.LongStringProperty(self, 'Description')

        self.addWidget(self.symbol_ctrl)
        self.addWidget(self.desc_ctrl)

        self.symbol_ctrl.propertyChanged.connect(self._on_symbol)
        self.desc_ctrl.propertyChanged.connect(self._on_desc)

    def set_obj(self, db_obj: PlatingMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PlatingMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')

            self.symbol_ctrl.setEnabled(False)
            self.desc_ctrl.setEnabled(False)
        else:
            plating = getattr(db_obj, self.attribute_name)

            db_obj.table.execute(f'SELECT symbol FROM platings;')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue(plating.symbol)
            self.desc_ctrl.SetValue(plating.description)

            self.symbol_ctrl.setEnabled(True)
            self.desc_ctrl.setEnabled(True)

    def _on_symbol(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the symbol event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        symbol = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, description FROM platings WHERE symbol="{symbol}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.platings_table.insert(symbol, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(symbol)
            self.choices.sort()

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue(symbol)

        self.desc_ctrl.SetValue(desc)

        setattr(self.db_obj, self.attribute_name + '_id', db_id)

    def SetAttributeName(self, name):
        """Execute the set attribute name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: UNKNOWN
        """
        self.attribute_name = name

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        getattr(self.db_obj, self.attribute_name).description = desc
