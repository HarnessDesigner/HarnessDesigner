# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from collections.abc import Callable
from typing import TYPE_CHECKING, Union as _Union

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import plating as _plating
    from PySide6 import QtWidgets


class PlatingMixin(BaseMixin):
    """Represent a plating mixin in :mod:`harness_designer.database.global_db.mixins.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_plating: _Union[DefaultStoredValueType, "_plating.Plating"] = DefaultStoredValue

    @property
    @_check_types.do
    def plating(self) -> "_plating.Plating":
        """Return the plating.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_plating.Plating`
        """
        if self._stored_plating is DefaultStoredValue:
            self._stored_plating = self._table.db.platings_table[self.plating_id]

        return self._stored_plating

    _stored_plating_id: bytes | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def plating_id(self) -> bytes:
        """Return the plating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        if self._stored_plating_id is DefaultStoredValue:
            self._stored_plating_id = self._table.select('plating_id', id=self._db_id)[0][0]

        return self._stored_plating_id

    @plating_id.setter
    @_check_types.do
    def plating_id(self, value: bytes) -> None:
        """Set the plating ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_plating_id = value
        self._stored_plating = DefaultStoredValue
        self._table.update(self._db_id, plating_id=value)
        self._populate('plating_id')


def _plating_of(db_obj: "PlatingMixin") -> _Union["_plating.Plating", None]:
    return db_obj.plating


def _set_plating_id(db_obj: "PlatingMixin", db_id: bytes) -> None:
    db_obj.plating_id = db_id


class PlatingControl(_prop_ctrls.Category):
    """Represent a plating control in :mod:`harness_designer.database.global_db.mixins.plating`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`PlatingControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Plating')

        self._get_target: Callable[[PlatingMixin], _Union["_plating.Plating", None]] = _plating_of
        self._set_target_id: Callable[[PlatingMixin, bytes], None] = _set_plating_id

        self.choices: list[str] = []
        self.db_obj: PlatingMixin | None = None

        self.symbol_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Symbol')
        self.desc_ctrl = _prop_ctrls.LongStringProperty(self, 'Description')

        self.addWidget(self.symbol_ctrl)
        self.addWidget(self.desc_ctrl)

        self.symbol_ctrl.propertyChanged.connect(self._on_symbol)
        self.desc_ctrl.propertyChanged.connect(self._on_desc)

    @_check_types.do
    def set_obj(self, db_obj: PlatingMixin | None) -> None:
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
            plating = self._get_target(db_obj)

            db_obj.table.execute(f'SELECT symbol FROM platings;')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue(plating.symbol)
            self.desc_ctrl.SetValue(plating.description)

            self.symbol_ctrl.setEnabled(True)
            self.desc_ctrl.setEnabled(True)

    @_check_types.do
    def _on_symbol(self, evt: _prop_ctrls.PropertyEvent) -> None:
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

        self._set_target_id(self.db_obj, db_id)

    @_check_types.do
    def SetTarget(self, get_target: Callable[[PlatingMixin], _Union["_plating.Plating", None]],
                  set_target_id: Callable[[PlatingMixin, bytes], None]) -> None:
        """Choose which plating of the db object this control edits.

        :param get_target: Returns the plating object on the db object.
        :param set_target_id: Stores the id of a plating on the db object.
        """
        self._get_target = get_target
        self._set_target_id = set_target_id

    @_check_types.do
    def _on_desc(self, evt: _prop_ctrls.PropertyEvent) -> None:
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        self._get_target(self.db_obj).description = desc
