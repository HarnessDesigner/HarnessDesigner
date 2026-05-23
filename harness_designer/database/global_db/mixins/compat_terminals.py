# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import terminal as _terminal


class CompatTerminalsMixin(BaseMixin):
    """Represent a compat terminals mixin in :mod:`harness_designer.database.global_db.mixins.compat_terminals`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        """Return the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_terminal.Terminal']
        """
        compat_terminals = self.compat_terminals_array
        res = []
        for part_number in compat_terminals:
            try:
                res.append(self._table.db.terminals_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_terminals_array(self) -> list[str]:
        """Return the compat terminals array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_terminals', id=self._db_id)[0][0]
        if value.startswith('[') and value.endswith(']'):
            value = value[1:-1]

        return value.split(', ')

    @compat_terminals_array.setter
    def compat_terminals_array(self, value: list[str]):
        """Set the compat terminals array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
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

        self.property_changed.connect(self._on_compat_housings)

    def set_obj(self, db_obj: CompatTerminalsMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CompatTerminalsMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue([])
            self.Enable(False)
        else:
            self.SetValue(db_obj.compat_terminals_array)
            self.Enable(True)

    def _on_compat_housings(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat housings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_terminals = evt.GetValue()
        self.db_obj.compat_terminals_array = compat_terminals
