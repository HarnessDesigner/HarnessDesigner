# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin


class SmoothMixin(BaseMixin):
    """Represent a smooth mixin in :mod:`harness_designer.database.project_db.mixins.smooth`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def smooth(self) -> bool | None:
        """
        Return whether to use smooth shading.

        If the return is None then the global smoothing option is used.

        :rtype: bool | None
        """
        value = self._table.select('smooth', id=self._db_id)[0][0]
        if value is not None:
            value = bool(value)

        return value

    @smooth.setter
    def smooth(self, value: bool | None):
        """
        Set whether to use smooth shading for this opject.

        Set to None to use the global shading setting if available.

        :type value: bool | None
        """

        if value is not None:
            value = int(value)

        self._table.update(self._db_id, smooth=value)
        self._populate('smooth')


class SmoothControl(_prop_ctrls.TriStateCheckboxProperty):
    """
    Represent a smooth control in :mod:`harness_designer.database.project_db.mixins.smooth`.
    """

    def __init__(self, parent):
        """Initialise the :class:`SmoothControl` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: SmoothMixin = None

        super().__init__(parent, 'Smooth')

        self.propertyChanged.connect(self._on_smooth)

    def _on_smooth(self, evt):
        """
        Handle the smooth event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.smooth = value

    def set_obj(self, db_obj: SmoothMixin):
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
