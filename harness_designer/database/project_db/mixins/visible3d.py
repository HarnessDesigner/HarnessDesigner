# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from .... import check_types as _check_types


if TYPE_CHECKING:
    from ....ui.prop_ctrls import events as _prop_events
    from PySide6 import QtWidgets


class Visible3DMixin(BaseMixin):
    """Represent a visible 3dmixin in :mod:`harness_designer.database.project_db.mixins.visible3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    @property
    @_check_types.do
    def is_visible3d(self) -> bool:
        """Return the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        _rows = self._table.select('is_visible3d', id=self._db_id)
        return bool(_rows[0][0]) if _rows else None

    @is_visible3d.setter
    @_check_types.do
    def is_visible3d(self, value: bool) -> None:
        """Set the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible3d=int(value))
        self._populate('is_visible3d')


class Visible3DControl(_prop_ctrls.BoolProperty):
    """Represent a visible 3dcontrol in :mod:`harness_designer.database.project_db.mixins.visible3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`Visible3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Visible3DMixin | None = None

        super().__init__(parent, 'Is Visible 3D')

        self.propertyChanged.connect(self._on_visible3d)

    @_check_types.do
    def _on_visible3d(self, evt: "_prop_events.PropertyEvent") -> None:
        """Handle the visible 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.is_visible3d = value

    @_check_types.do
    def set_obj(self, db_obj: Visible3DMixin | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Visible3DMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.is_visible3d)
            self.setEnabled(True)
