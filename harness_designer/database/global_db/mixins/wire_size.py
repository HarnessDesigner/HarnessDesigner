# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin

from .... import utils as _utils
from ....ui import prop_ctrls as _prop_ctrls


class WireSizeMixin(BaseMixin):
    """Represent a wire size mixin in :mod:`harness_designer.database.global_db.mixins.wire_size`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def wire_size_dia_min(self) -> float | None:
        """Return the wire size dia min.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float | None
        """
        return self._table.select('wire_size_dia_min', id=self._db_id)[0][0]

    @wire_size_dia_min.setter
    def wire_size_dia_min(self, value: float):
        """Set the wire size dia min.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_dia_min=value)
        self._table.update(self._db_id, wire_size_cross_min=_utils.d_mm_to_mm2(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.d_mm_to_awg(value))
        self._populate('wire_size_dia_min')

    @property
    def wire_size_dia_max(self) -> float | None:
        """Return the wire size dia max.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float | None
        """
        return self._table.select('wire_size_dia_max', id=self._db_id)[0][0]

    @wire_size_dia_max.setter
    def wire_size_dia_max(self, value: float):
        """Set the wire size dia max.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_dia_max=value)
        self._table.update(self._db_id, wire_size_cross_min=_utils.d_mm_to_mm2(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.d_mm_to_awg(value))
        self._populate('wire_size_dia_max')

    @property
    def wire_size_cross_min(self) -> float | None:
        """Return the wire size cross min.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float | None
        """
        return self._table.select('wire_size_cross_min', id=self._db_id)[0][0]

    @wire_size_cross_min.setter
    def wire_size_cross_min(self, value: float):
        """Set the wire size cross min.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_cross_min=value)
        self._table.update(self._db_id, wire_size_dia_min=_utils.mm2_to_d_mm(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.mm2_to_awg(value))
        self._populate('wire_size_cross_min')

    @property
    def wire_size_cross_max(self) -> float | None:
        """Return the wire size cross max.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float | None
        """
        return self._table.select('wire_size_cross_max', id=self._db_id)[0][0]

    @wire_size_cross_max.setter
    def wire_size_cross_max(self, value: float):
        """Set the wire size cross max.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, wire_size_cross_max=value)
        self._table.update(self._db_id, wire_size_dia_max=_utils.mm2_to_d_mm(value))
        self._table.update(self._db_id, wire_size_awg_max=_utils.mm2_to_awg(value))
        self._populate('wire_size_cross_max')

    @property
    def wire_size_awg_min(self) -> int | None:
        """Return the wire size awg min.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        return self._table.select('wire_size_awg_min', id=self._db_id)[0][0]

    @wire_size_awg_min.setter
    def wire_size_awg_min(self, value: int):
        """Set the wire size awg min.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, wire_size_awg_min=value)
        self._table.update(self._db_id, wire_size_dia_min=_utils.awg_to_d_mm(value))
        self._table.update(self._db_id, wire_size_cross_min=_utils.awg_to_mm2(value))
        self._populate('wire_size_awg_min')

    @property
    def wire_size_awg_max(self) -> int | None:
        """Return the wire size awg max.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        return self._table.select('wire_size_awg_max', id=self._db_id)[0][0]

    @wire_size_awg_max.setter
    def wire_size_awg_max(self, value: int):
        """Set the wire size awg max.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, wire_size_awg_max=value)
        self._table.update(self._db_id, wire_size_dia_max=_utils.awg_to_d_mm(value))
        self._table.update(self._db_id, wire_size_cross_max=_utils.awg_to_mm2(value))
        self._populate('wire_size_awg_max')


class WireSizeControl(_prop_ctrls.Category):
    """Represent a wire size control in :mod:`harness_designer.database.global_db.mixins.wire_size`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: WireSizeMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`WireSizeMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.min_dia_ctrl.SetValue(0.254)
            self.max_dia_ctrl.SetValue(0.254)

            self.min_awg_ctrl.SetValue(30)
            self.max_awg_ctrl.SetValue(30)

            self.min_mm2_ctrl.SetValue(0.0507)
            self.max_mm2_ctrl.SetValue(0.0507)

            self.min_dia_ctrl.setEnabled(False)
            self.max_dia_ctrl.setEnabled(False)

            self.min_awg_ctrl.setEnabled(False)
            self.max_awg_ctrl.setEnabled(False)

            self.min_mm2_ctrl.setEnabled(False)
            self.max_mm2_ctrl.setEnabled(False)
        else:
            self.min_dia_ctrl.SetValue(db_obj.wire_size_dia_min)
            self.max_dia_ctrl.SetValue(db_obj.wire_size_dia_max)

            self.min_awg_ctrl.SetValue(db_obj.wire_size_awg_min)
            self.max_awg_ctrl.SetValue(db_obj.wire_size_awg_max)

            self.min_mm2_ctrl.SetValue(db_obj.wire_size_cross_min)
            self.max_mm2_ctrl.SetValue(db_obj.wire_size_cross_max)

            self.min_dia_ctrl.setEnabled(True)
            self.max_dia_ctrl.setEnabled(True)

            self.min_awg_ctrl.setEnabled(True)
            self.max_awg_ctrl.setEnabled(True)

            self.min_mm2_ctrl.setEnabled(True)
            self.max_mm2_ctrl.setEnabled(True)

    def _on_min_mm2(self, evt):
        """Handle the min mm 2 event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mm2 = evt.GetValue()

        self.db_obj.wire_size_cross_min = mm2
        self.min_awg_ctrl.SetValue(self.db_obj.wire_size_awg_min)
        self.min_dia_ctrl.SetValue(self.db_obj.wire_size_dia_min)

    def _on_max_mm2(self, evt):
        """Handle the max mm 2 event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        mm2 = evt.GetValue()

        self.db_obj.wire_size_cross_max = mm2
        self.max_awg_ctrl.SetValue(self.db_obj.wire_size_awg_max)
        self.max_dia_ctrl.SetValue(self.db_obj.wire_size_dia_max)

    def _on_min_awg(self, evt):
        """Handle the min awg event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        awg = evt.GetValue()

        self.db_obj.wire_size_awg_min = awg
        self.min_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_min)
        self.min_dia_ctrl.SetValue(self.db_obj.wire_size_dia_min)

    def _on_max_awg(self, evt):
        """Handle the max awg event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        awg = evt.GetValue()
        
        self.db_obj.wire_size_awg_max = awg

        self.max_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_max)
        self.max_dia_ctrl.SetValue(self.db_obj.wire_size_dia_max)       

    def _on_min_dia(self, evt):
        """Handle the min dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        dia = evt.GetValue()

        self.db_obj.wire_size_dia_min = dia
        self.min_awg_ctrl.SetValue(self.db_obj.wire_size_awg_min)
        self.min_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_min)

    def _on_max_dia(self, evt):
        """Handle the max dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        dia = evt.GetValue()

        self.db_obj.wire_size_dia_max = dia
        self.max_awg_ctrl.SetValue(self.db_obj.wire_size_awg_max)
        self.max_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_max)
    
    def __init__(self, parent):
        """Initialise the :class:`WireSizeControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: WireSizeMixin = None

        super().__init__(parent, 'Wire Sizes')

        self.min_mm2_ctrl = _prop_ctrls.FloatProperty(
            self, 'Minimum Cross', min_value=0.0507, max_value=135.1755, increment=0.0001, units='mm²')

        self.max_mm2_ctrl = _prop_ctrls.FloatProperty(
            self, 'Maximum Cross', min_value=0.0507, max_value=135.1755, increment=0.0001, units='mm²')

        self.min_awg_ctrl = _prop_ctrls.IntProperty(
            self, 'Minimum AWG', min_value=-4, max_value=30, units='awg')

        self.max_awg_ctrl = _prop_ctrls.IntProperty(
            self, 'Maximum AWG', min_value=-4, max_value=30, units='awg')

        self.min_dia_ctrl = _prop_ctrls.FloatProperty(
            self, 'Minimum Diameter', min_value=0.254, max_value=13.1191, increment=0.0001, units='mm')

        self.max_dia_ctrl = _prop_ctrls.FloatProperty(
            self, 'Maximum Diameter', min_value=0.254, max_value=13.1191, increment=0.0001, units='mm')

        self.addWidget(self.min_mm2_ctrl)
        self.addWidget(self.max_mm2_ctrl)

        self.min_mm2_ctrl.propertyChanged.connect(self._on_min_mm2)
        self.max_mm2_ctrl.propertyChanged.connect(self._on_max_mm2)

        self.addWidget(self.min_awg_ctrl)
        self.addWidget(self.max_awg_ctrl)

        self.min_awg_ctrl.propertyChanged.connect(self._on_min_awg)
        self.max_awg_ctrl.propertyChanged.connect(self._on_max_awg)

        self.addWidget(self.min_dia_ctrl)
        self.addWidget(self.max_dia_ctrl)

        self.min_dia_ctrl.propertyChanged.connect(self._on_min_dia)
        self.max_dia_ctrl.propertyChanged.connect(self._on_max_dia)
