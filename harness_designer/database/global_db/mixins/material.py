# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import material as _material


class MaterialMixin(BaseMixin):
    """Represent a material mixin in :mod:`harness_designer.database.global_db.mixins.material`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def material(self) -> "_material.Material":
        """Return the material.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_material.Material`
        """
        material_id = self._table.select('material_id', id=self._db_id)
        return self._table.db.materials_table[material_id[0][0]]

    @property
    def material_id(self) -> int:
        """Return the material ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('material_id', id=self._db_id)[0][0]

    @material_id.setter
    def material_id(self, value: int):
        """Set the material ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, material_id=value)
        self._populate('material_id')


class MaterialControl(_prop_ctrls.ComboBoxProperty):
    """Represent a material control in :mod:`harness_designer.database.global_db.mixins.material`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`MaterialControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: MaterialMixin = None
        self.choices: list[str] = []

        super().__init__(parent, 'Material')
        self.property_changed.connect(self._on_material)

    def set_obj(self, db_obj: MaterialMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`MaterialMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems(self.choices)
            self.SetValue('')
            self.Enable(False)
        else:
            db_obj.table.execute('SELECT name FROM materials;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.material.name)
            self.Enable(True)

    def _on_material(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the material event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM materials WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.materials_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.material_id = db_id

