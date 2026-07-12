# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


class Visible3DMixin(BaseMixin):
    """Represent a visible 3dmixin in :mod:`harness_designer.database.project_db.mixins.visible3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_is_visible3d: bool | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def is_visible3d(self) -> bool:
        """Return the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        if self._stored_is_visible3d is DefaultStoredValue: 
            self._stored_is_visible3d = bool(self._table.select('is_visible3d', id=self._db_id)[0][0])
        
        return self._stored_is_visible3d

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        """Set the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._stored_is_visible3d = value
        
        self._table.update(self._db_id, is_visible3d=int(value))
        self._populate('is_visible3d')


class Visible3DControl(_prop_ctrls.BoolProperty):
    """Represent a visible 3dcontrol in :mod:`harness_designer.database.project_db.mixins.visible3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`Visible3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Visible3DMixin = None

        super().__init__(parent, 'Is Visible 3D')

        self.propertyChanged.connect(self._on_visible3d)

    def _on_visible3d(self, evt):
        """Handle the visible 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.is_visible3d = value

    def set_obj(self, db_obj: Visible3DMixin):
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
