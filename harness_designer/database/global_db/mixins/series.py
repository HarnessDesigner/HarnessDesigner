# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin


if TYPE_CHECKING:
    from .. import series as _series  # NOQA


class SeriesMixin(BaseMixin):
    """Represent a series mixin in :mod:`harness_designer.database.global_db.mixins.series`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def series(self) -> "_series.Series":
        """Return the series.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_series.Series`
        """
        from .. import series as _series  # NOQA

        series_id = self._table.select('series_id', id=self._db_id)
        return _series.Series(self._table.db.series_table, series_id[0][0])

    @property
    def series_id(self) -> int:
        """Return the series ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('series_id', id=self._db_id)[0][0]

    @series_id.setter
    def series_id(self, value: int):
        """Set the series ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, series_id=value)
        self._populate('series_id')


class SeriesControl(_prop_ctrls.Category):
    """Represent a series control in :mod:`harness_designer.database.global_db.mixins.series`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`SeriesControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Series')

        self.choices: list[str] = []
        self.db_obj: SeriesMixin = None

        self.name_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Name')
        self.desc_ctrl = _prop_ctrls.LongStringProperty(self, 'Description')
        self.mfg_ctrl = _prop_ctrls.StringProperty(self, 'Manufacturer', read_only=True)

        self.name_ctrl.property_changed.connect(self._on_name)
        self.desc_ctrl.property_changed.connect(self._on_desc)

    def set_obj(self, db_obj: SeriesMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`SeriesMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.name_ctrl.SetItems([])
            self.name_ctrl.SetValue('')
            self.mfg_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')
            self.name_ctrl.Enable(False)
            self.mfg_ctrl.Enable(False)
            self.desc_ctrl.Enable(False)
        else:
            series = db_obj.series
            mfg_id = series.manufacturer.db_id

            db_obj.table.execute(f'SELECT name FROM series WHERE mfg_id={mfg_id};')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(series.name)
            self.mfg_ctrl.SetValue(series.manufacturer.name)
            self.desc_ctrl.SetValue(series.description)

            self.name_ctrl.Enable(True)
            self.mfg_ctrl.Enable(True)
            self.desc_ctrl.Enable(True)

    def _on_name(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the name event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()
        mfg_id = self.db_obj.series.mfg_id

        self.db_obj.table.execute(f'SELECT id, description FROM series WHERE name="{name}" AND mfg_id={mfg_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.series_table.insert(name, mfg_id, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)

        self.db_obj.series_id = db_id

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the desc event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        desc = evt.GetValue()
        self.db_obj.series.description = desc
