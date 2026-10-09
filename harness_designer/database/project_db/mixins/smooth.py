# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from .... import check_types as _check_types


if TYPE_CHECKING:
    from ....ui.prop_ctrls import events as _prop_events
    from PySide6 import QtWidgets


class SmoothMixin(BaseMixin):
    """Represent a smooth mixin in :mod:`harness_designer.database.project_db.mixins.smooth`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    @property
    @_check_types.do
    def smooth(self) -> bool | None:
        """
        Return whether to use smooth shading.

        If the return is None then the global smoothing option is used.

        :rtype: bool | None
        """
        _rows = self._table.select('smooth', id=self._db_id)
        value = _rows[0][0] if _rows else None
        if value is not None:
            value = bool(value)

        return value

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        """
        Set whether to use smooth shading for this opject.

        Set to None to use the global shading setting if available.

        :type value: bool | None
        """
        real_value = value
        if real_value is not None:
            real_value = int(real_value)

        self._table.update(self._db_id, smooth=real_value)
        self._populate('smooth')


class SmoothControl(_prop_ctrls.TriStateCheckboxProperty):
    """
    Represent a smooth control in :mod:`harness_designer.database.project_db.mixins.smooth`.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`SmoothControl` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: SmoothMixin | None = None

        super().__init__(parent, 'Smooth')

        self.propertyChanged.connect(self._on_smooth)

    @_check_types.do
    def _on_smooth(self, evt: "_prop_events.PropertyEvent") -> None:
        """
        Handle the smooth event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.smooth = value

    @_check_types.do
    def set_obj(self, db_obj: SmoothMixin | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`SmoothMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.smooth)
            self.setEnabled(True)
