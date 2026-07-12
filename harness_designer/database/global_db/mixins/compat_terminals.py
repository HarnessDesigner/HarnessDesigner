# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import terminal as _terminal


class CompatTerminalsMixin(BaseMixin):
    """Represent a compat terminals mixin in :mod:`harness_designer.database.global_db.mixins.compat_terminals`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_compat_terminals: list["_terminal.Terminal"] | DefaultStoredValueType = DefaultStoredValue

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        """Return the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_terminal.Terminal']
        """
        if self._stored_compat_terminals is DefaultStoredValue:
            part_numbers = [pn for pn in self.compat_terminals_array if pn]

            if not part_numbers:
                self._stored_compat_terminals = []
            else:
                from .. import terminal as _terminal_module

                terminals_table = self._table.db.terminals_table
                placeholders = ', '.join('?' * len(part_numbers))
                terminals_table.execute(
                    f'SELECT id, part_number FROM terminals WHERE part_number IN ({placeholders});',
                    part_numbers
                )
                found = {part_number: db_id for db_id, part_number in terminals_table.fetchall()}

                self._stored_compat_terminals = [
                    _terminal_module.Terminal(terminals_table, found[pn])
                    for pn in part_numbers if pn in found
                ]

        return self._stored_compat_terminals

    _stored_compat_terminals_array: list[str] | DefaultStoredValueType = DefaultStoredValue

    @property
    def compat_terminals_array(self) -> list[str]:
        """Return the compat terminals array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        if self._stored_compat_terminals_array is DefaultStoredValue:
            value = self._table.select('compat_terminals', id=self._db_id)[0][0]

            if value.startswith('['):
                value = value[1:-1]

            self._stored_compat_terminals_array = value.split(', ')

        return self._stored_compat_terminals_array

    @compat_terminals_array.setter
    def compat_terminals_array(self, value: list[str]):
        """Set the compat terminals array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        self._stored_compat_terminals_array = value
        self._stored_compat_terminals = DefaultStoredValue
        value = ', '.join(value)

        self._table.update(self._db_id, compat_terminals=value)
        self._populate('compat_terminals_array')


class CompatTerminalsControl(_prop_ctrls.ArrayStringProperty):
    """Represent a compat terminals control in :mod:`harness_designer.database.global_db.mixins.compat_terminals`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`CompatTerminalsControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: CompatTerminalsMixin = None
        super().__init__(parent, 'Compatible Terminals')

        self.propertyChanged.connect(self._on_compat_housings)

    def set_obj(self, db_obj: CompatTerminalsMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CompatTerminalsMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue([])
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.compat_terminals_array)
            self.setEnabled(True)

    def _on_compat_housings(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat housings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_terminals = evt.GetValue()
        self.db_obj.compat_terminals_array = compat_terminals
