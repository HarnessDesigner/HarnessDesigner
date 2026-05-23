# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


class DescriptionMixin(BaseMixin):
    """Represent a description mixin in :mod:`harness_designer.database.global_db.mixins.description`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def description(self) -> str:
        """Return the description.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        """Set the description.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, description=value)
        self._populate('description')


class DescriptionControl(_prop_ctrls.LongStringProperty):
    """Represent a description control in :mod:`harness_designer.database.global_db.mixins.description`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`DescriptionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: DescriptionMixin = None

        super().__init__(parent, 'Description')

        self.property_changed.connect(self._on_desc)

    def set_obj(self, db_obj: DescriptionMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`DescriptionMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.Enable(False)
        else:
            self.SetValue(db_obj.description)
            self.Enable(True)

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        self.db_obj.description = desc
