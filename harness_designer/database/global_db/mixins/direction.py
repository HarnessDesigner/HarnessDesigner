# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import direction as _direction  # NOQA


class DirectionMixin(BaseMixin):
    """Represent a direction mixin in :mod:`harness_designer.database.global_db.mixins.direction`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def direction(self) -> "_direction.Direction":
        """Return the direction.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_direction.Direction`
        """
        from .. import direction as _direction  # NOQA

        direction_id = self._table.select('direction_id', id=self._db_id)
        return _direction.Direction(self._table.db.directions_table, direction_id[0][0])

    @property
    def direction_id(self) -> int:
        """Return the direction ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('direction_id', id=self._db_id)[0][0]

    @direction_id.setter
    def direction_id(self, value: int):
        """Set the direction ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, direction_id=value)
        self._populate('direction_id')


class DirectionControl(_prop_ctrls.ComboBoxProperty):
    """Represent a direction control in :mod:`harness_designer.database.global_db.mixins.direction`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`DirectionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """

        self.choices: list[str] = []
        self.db_obj: DirectionMixin = None

        super().__init__(parent, 'Direction')
        self.propertyChanged.connect(self._on_direction)

    def set_obj(self, db_obj: DirectionMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`DirectionMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems([])
            self.SetValue('')
            self.setEnabled(False)
        else:
            db_obj.table.execute('SELECT name FROM directions;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.direction.name)
            self.setEnabled(True)

    def _on_direction(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the direction event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM directions WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.directions_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.direction_id = db_id
