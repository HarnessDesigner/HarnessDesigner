# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_type as _wire_type
    from PySide6 import QtWidgets


class WireTypeMixin(BaseMixin):
    """Adds the ``wire_type`` / ``wire_type_id`` columns of a wire to a database entry."""

    _stored_wire_type: _Union[DefaultStoredValueType, "_wire_type.WireType"] = DefaultStoredValue

    @property
    @_check_types.do
    def wire_type(self) -> "_wire_type.WireType":
        """The wire type row this entry points at."""
        if self._stored_wire_type is DefaultStoredValue:
            wire_type_id = self._table.select('wire_type_id', id=self._db_id)
            self._stored_wire_type = self._table.db.wire_types_table[wire_type_id[0][0]]

        return self._stored_wire_type

    _stored_wire_type_id: bytes | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def wire_type_id(self) -> bytes:
        """The id of the wire type row this entry points at."""
        if self._stored_wire_type_id is DefaultStoredValue:
            self._stored_wire_type_id = self._table.select('wire_type_id', id=self._db_id)[0][0]

        return self._stored_wire_type_id

    @wire_type_id.setter
    @_check_types.do
    def wire_type_id(self, value: bytes) -> None:
        """Point this entry at another wire type row.

        :param value: Row id of the wire type.
        """
        self._stored_wire_type_id = value
        self._stored_wire_type = DefaultStoredValue

        self._table.update(self._db_id, wire_type_id=value)
        self._populate('wire_type_id')


class WireTypeControl(_prop_ctrls.ComboBoxProperty):
    """Combo box that picks a wire's type; typing a new name adds it to the wire types table."""

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget"):
        """Create the control.

        :param parent: Parent widget.
        """
        self.db_obj: WireTypeMixin | None = None
        self.choices: list[str] = []

        super().__init__(parent, 'Wire Type')
        self.propertyChanged.connect(self._on_wire_type)

    @_check_types.do
    def set_obj(self, db_obj: WireTypeMixin | None) -> None:
        """Show the wire type of ``db_obj``; ``None`` clears and disables the control.

        :param db_obj: Database-backed object, or ``None``.
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems(self.choices)
            self.SetValue('')
            self.setEnabled(False)
        else:
            db_obj.table.execute('SELECT name FROM wire_types;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.wire_type.name)
            self.setEnabled(True)

    @_check_types.do
    def _on_wire_type(self, evt: _prop_ctrls.PropertyEvent) -> None:
        """Store the chosen wire type, adding a row for a name that is new.

        :param evt: Event carrying the chosen name.
        """
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM wire_types WHERE name=?;', (name,))
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.wire_types_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()
            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.wire_type_id = db_id
