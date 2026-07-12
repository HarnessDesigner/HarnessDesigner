# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....ui import prop_ctrls as _prop_ctrls


class NameMixin(BaseMixin):
    """Represent a name mixin in :mod:`harness_designer.database.project_db.mixins.name`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_name: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def name(self) -> str:
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_name is DefaultStoredValue:
            self._stored_name = self._table.select('name', id=self._db_id)[0][0]
            
        return self._stored_name

    @name.setter
    def name(self, value: str):
        """Set the name.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_name = value
        self._table.update(self._db_id, name=value)
        self._populate('name')


class NameControl(_prop_ctrls.StringProperty):
    """Represent a name control in :mod:`harness_designer.database.project_db.mixins.name`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`NameControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: NameMixin = None

        super().__init__(parent, 'Name')

        self.propertyChanged.connect(self._on_name)

    def _on_name(self, evt):
        """Handle the name event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.name = value

    def set_obj(self, db_obj: NameMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`NameMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.name)
            self.setEnabled(True)
