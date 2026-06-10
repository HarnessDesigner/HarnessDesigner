# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import cavity_lock as _cavity_lock  # NOQA


class CavityLockMixin(BaseMixin):
    """Represent a cavity lock mixin in :mod:`harness_designer.database.global_db.mixins.cavity_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def cavity_lock(self) -> "_cavity_lock.CavityLock":
        """Return the cavity lock.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_cavity_lock.CavityLock`
        """
        from ..cavity_lock import CavityLock
        lock_id = self.cavity_lock_id

        return CavityLock(self._table.db.cavity_locks_table, lock_id)

    @property
    def cavity_lock_id(self) -> int:
        """Return the cavity lock ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value: int):
        """Set the cavity lock ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, cavity_lock_id=value)
        self._populate('cavity_lock_id')


class CavityLockControl(_prop_ctrls.Property):
    """Represent a cavity lock control in :mod:`harness_designer.database.global_db.mixins.cavity_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`CavityLockControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Cavity Lock', orientation='vertical')
        self.db_obj: CavityLockMixin = None
        self.choices: list[str] = []

        self.name_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Name')
        self.desc_ctrl = _prop_ctrls.StringProperty(self, 'Description')

        self.addWidget(self.name_ctrl)
        self.addWidget(self.desc_ctrl)
        self.name_ctrl.propertyChanged.connect(self._on_name)
        self.desc_ctrl.propertyChanged.connect(self._on_desc)

    def set_obj(self, db_obj: CavityLockMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CavityLockMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')
            self.name_ctrl.setEnabled(False)
            self.desc_ctrl.setEnabled(False)
        else:
            db_obj.table.execute(f'SELECT name FROM cavity_locks;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(db_obj.cavity_lock.name)
            self.desc_ctrl.SetValue(db_obj.cavity_lock.description)
            self.name_ctrl.setEnabled(True)
            self.desc_ctrl.setEnabled(True)

    def _on_name(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the name event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, description FROM cavity_locks WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.cavity_locks_table.insert(name, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.db_obj.cavity_lock_id = db_id
        self.desc_ctrl.SetValue(desc)

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        self.db_obj.cavity_lock.description = desc
