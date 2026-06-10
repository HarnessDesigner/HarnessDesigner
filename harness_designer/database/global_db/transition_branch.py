# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING


from ...ui import prop_ctrls as _prop_ctrls
from .bases import EntryBase, TableBase
from .mixins import NameMixin, NameControl
from ...geometry import point as _point


if TYPE_CHECKING:
    from . import transition as _transition
    from . import bundle_cover as _bundle_cover


class TransitionBranchesTable(TableBase):
    """Represent a transition branches table in :mod:`harness_designer.database.global_db.transition_branch`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'transition_branches'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import transition_branches

        return transition_branches.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        from ..create_database import transition_branches

        transition_branches.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transition_branches

        transition_branches.table.update_fields(self)

    def __iter__(self) -> _Iterable["TransitionBranch"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['TransitionBranch']
        """
        for db_id in TableBase.__iter__(self):
            yield TransitionBranch(self, db_id)

    def __getitem__(self, item) -> "TransitionBranch":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`TransitionBranch`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return TransitionBranch(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, transition_id: int, idx: int, name: int, bulb_offset: _point.Point | None,
               bulb_length: float | None, min_dia: float, max_dia: float, length: float,
               angle: float, offset: _point.Point | None, flange_height: float | None,
               flange_width: float | None) -> "TransitionBranch":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param transition_id: Identifier for the transition.
        :type transition_id: int
        :param idx: Value for ``idx``.
        :type idx: int
        :param name: Name value.
        :type name: int
        :param bulb_offset: Value for ``bulb_offset``.
        :type bulb_offset: _point.Point | None
        :param bulb_length: Value for ``bulb_length``.
        :type bulb_length: float | None
        :param min_dia: Value for ``min_dia``.
        :type min_dia: float
        :param max_dia: Value for ``max_dia``.
        :type max_dia: float
        :param length: Value for ``length``.
        :type length: float
        :param angle: Value for ``angle``.
        :type angle: float
        :param offset: Value for ``offset``.
        :type offset: _point.Point | None
        :param flange_height: Value for ``flange_height``.
        :type flange_height: float | None
        :param flange_width: Value for ``flange_width``.
        :type flange_width: float | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`TransitionBranch`
        """

        db_id = TableBase.insert(self, transition_id=transition_id, idx=idx, name=name,
                                 bulb_offset=bulb_offset, bulb_length=bulb_length,
                                 min_dia=min_dia, max_dia=max_dia,
                                 length=length, angle=angle, offset=offset,
                                 flange_height=flange_height, flange_width=flange_width)

        return TransitionBranch(self, db_id)


class TransitionBranch(EntryBase, NameMixin):
    """Represent a transition branch in :mod:`harness_designer.database.global_db.transition_branch`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: TransitionBranchesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'transition_branches': [self.db_id],
            'transitions': [self.transition_id]
        }

        return packet

    @property
    def transition(self) -> "_transition.Transition":
        """Return the transition.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_transition.Transition`
        """
        from .transition import Transition

        tran_id = self.transition_id

        return Transition(self._table.db.transitions_table, tran_id)

    @property
    def transition_id(self) -> int:
        """Return the transition ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('tran_id', id=self._db_id)[0][0]

    @property
    def idx(self) -> int:
        """Return the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        """Set the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    def bulb_offset(self) -> _point.Point:
        """Return the bulb offset.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        offset = self._table.select('bulb_offset', id=self._db_id)[0][0]
        if offset is None:
            return _point.Point(0.0, 0.0)

        offset = eval(offset)

        return _point.Point(offset[0], offset[1], 0)

    @bulb_offset.setter
    def bulb_offset(self, value: _point.Point):
        """Set the bulb offset.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: :class:`_point.Point`
        """
        self._table.update(self._db_id, bulb_offset=str(list(value.as_float)))
        self._populate('bulb_offset')

    @property
    def bulb_length(self) -> float:
        """Return the bulb length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        length = self._table.select('bulb_length', id=self._db_id)[0][0]

        if length is None:
            return 0.0

        return length

    @bulb_length.setter
    def bulb_length(self, value: float):
        """Set the bulb length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, bulb_length=value)
        self._populate('bulb_length')

    @property
    def compat_bundle_covers(self) -> list["_bundle_cover.BundleCover"]:
        """Return the compat bundle covers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_bundle_cover.BundleCover']
        """
        min_dia = self.min_dia
        max_dia = self.max_dia

        res = []

        for bundle_cover in self._table.db.bundle_covers_table:
            if bundle_cover.min_dia < max_dia and bundle_cover.max_dia > min_dia:
                res.append(bundle_cover)

        return res

    @property
    def min_dia(self) -> float:
        """Return the min dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        min_dia = self._table.select('min_dia', id=self._db_id)[0][0]
        return min_dia

    @min_dia.setter
    def min_dia(self, value: float):
        """Set the min dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, min_dia=value)
        self._populate('min_dia')

    @property
    def max_dia(self) -> float:
        """Return the max dia.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        max_dia = self._table.select('max_dia', id=self._db_id)[0][0]
        return max_dia

    @max_dia.setter
    def max_dia(self, value: float):
        """Set the max dia.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, max_dia=value)
        self._populate('max_dia')

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        length = self._table.select('length', id=self._db_id)[0][0]
        return length

    @length.setter
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, length=value)
        self._populate('length')

    @property
    def angle(self) -> float:
        """Return the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        angle = self._table.select('angle', id=self._db_id)[0][0]
        return angle

    @angle.setter
    def angle(self, value: float):
        """Set the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, angle=float(value))
        self._populate('angle')

    @property
    def offset(self) -> _point.Point:
        """Return the offset.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        offset = self._table.select('offset', id=self._db_id)[0][0]
        if offset is None:
            return None

        offset = eval(offset)

        return _point.Point(offset[0], offset[1], 0)

    @offset.setter
    def offset(self, value: _point.Point):
        """Set the offset.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: :class:`_point.Point`
        """
        self._table.update(self._db_id, offset=str(list(value.as_float)))
        self._populate('offset')

    @property
    def flange_height(self) -> float:
        """Return the flange height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        flange_height = self._table.select('flange_height', id=self._db_id)[0][0]
        return flange_height

    @flange_height.setter
    def flange_height(self, value: float):
        """Set the flange height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, flange_height=value)
        self._populate('flange_height')

    @property
    def flange_width(self) -> float:
        """Return the flange width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        flange_width = self._table.select('flange_width', id=self._db_id)[0][0]
        return flange_width

    @flange_width.setter
    def flange_width(self, value: float):
        """Set the flange width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, flange_width=value)
        self._populate('flange_width')


class TransitionBranchControl(_prop_ctrls.Category):
    """Represent a transition branch control in :mod:`harness_designer.database.global_db.transition_branch`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: TransitionBranch):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`TransitionBranch`
        """
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.length_ctrl.SetValue(0.01)
            self.angle_ctrl.SetValue(0.0)
            self.offset_ctrl.SetValue(None)
            self.bulb_offset_ctrl.SetValue(None)
            self.bulb_length_ctrl.SetValue(0.0)
            self.min_dia_ctrl.SetValue(0.01)
            self.max_dia_ctrl.SetValue(0.01)
            self.flange_height_ctrl.SetValue(0.0)
            self.flange_width_ctrl.SetValue(0.0)

            self.length_ctrl.setEnabled(False)
            self.angle_ctrl.setEnabled(False)
            self.offset_ctrl.setEnabled(False)
            self.bulb_offset_ctrl.setEnabled(False)
            self.bulb_length_ctrl.setEnabled(False)
            self.min_dia_ctrl.setEnabled(False)
            self.max_dia_ctrl.setEnabled(False)
            self.flange_height_ctrl.setEnabled(False)
            self.flange_width_ctrl.setEnabled(False)
        else:
            self.length_ctrl.SetValue(db_obj.length)
            self.angle_ctrl.SetValue(db_obj.angle)
            self.offset_ctrl.SetValue(db_obj.offset)
            self.bulb_offset_ctrl.SetValue(db_obj.bulb_offset)
            self.bulb_length_ctrl.SetValue(db_obj.bulb_length)
            self.min_dia_ctrl.SetValue(db_obj.min_dia)
            self.max_dia_ctrl.SetValue(db_obj.max_dia)
            self.flange_height_ctrl.SetValue(db_obj.flange_height)
            self.flange_width_ctrl.SetValue(db_obj.flange_width)

            self.length_ctrl.setEnabled(True)
            self.angle_ctrl.setEnabled(True)
            self.offset_ctrl.setEnabled(True)
            self.bulb_offset_ctrl.setEnabled(True)
            self.bulb_length_ctrl.setEnabled(True)
            self.min_dia_ctrl.setEnabled(True)
            self.max_dia_ctrl.setEnabled(True)
            self.flange_height_ctrl.setEnabled(True)
            self.flange_width_ctrl.setEnabled(True)

    def _on_length(self, evt):
        """Handle the length event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.length = value

    def _on_angle(self, evt):
        """Handle the angle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.angle = value

    def _on_bulb_length(self, evt):
        """Handle the bulb length event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.bulb_length = value

    def _on_min_dia(self, evt):
        """Handle the min dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.min_dia = value

    def _on_max_dia(self, evt):
        """Handle the max dia event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.max_dia = value

    def _on_flange_height(self, evt):
        """Handle the flange height event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.flange_height = value

    def _on_flange_width(self, evt):
        """Handle the flange width event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.flange_width = value

    def SetIndex(self, index):
        """Execute the set index operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        """
        self.SetLabel(f'Branch {index}')

    def __init__(self, parent):
        """Initialise the :class:`TransitionBranchControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: TransitionBranch = None
        super().__init__(parent, 'Branch')

        self.name_ctrl = NameControl(self)

        self.addWidget(self.name_ctrl)

        self.length_ctrl = _prop_ctrls.FloatProperty(
            self, 'Length',
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        self.addWidget(self.length_ctrl)

        self.angle_ctrl = _prop_ctrls.FloatProperty(
            self, 'Angle', min_value=-180.0,
            max_value=180.0, increment=0.1, units='°')

        self.addWidget(self.angle_ctrl)

        self.offset_ctrl = _prop_ctrls.Position2DProperty(self, 'Offset')

        self.addWidget(self.offset_ctrl)

        bulb_group = _prop_ctrls.Property(self, f'Bulb', orientation='vertical')

        self.addWidget(bulb_group)

        self.bulb_offset_ctrl = _prop_ctrls.Position2DProperty(bulb_group, 'Offset')
        bulb_group.addWidget(self.bulb_offset_ctrl)

        self.bulb_length_ctrl = _prop_ctrls.FloatProperty(
            bulb_group, 'Length',
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        bulb_group.addWidget(self.bulb_length_ctrl)

        size_group = _prop_ctrls.Property(bulb_group, 'Diameter', orientation='vertical')

        self.addWidget(size_group)

        self.min_dia_ctrl = _prop_ctrls.FloatProperty(
            size_group, 'Minimum',
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        size_group.addWidget(self.min_dia_ctrl)

        self.max_dia_ctrl = _prop_ctrls.FloatProperty(
            size_group, 'Maximum',
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        size_group.addWidget(self.max_dia_ctrl)

        flange_group = _prop_ctrls.Property(self, 'Flange', orientation='vertical')

        self.addWidget(flange_group)

        self.flange_height_ctrl = _prop_ctrls.FloatProperty(
            flange_group, 'Height',
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        self.flange_width_ctrl = _prop_ctrls.FloatProperty(
            flange_group, 'Width',
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        flange_group.addWidget(self.flange_height_ctrl)
        flange_group.addWidget(self.flange_width_ctrl)

        self.length_ctrl.propertyChanged.connect(self._on_length)
        self.angle_ctrl.propertyChanged.connect(self._on_angle)
        self.bulb_length_ctrl.propertyChanged.connect(self._on_bulb_length)
        self.min_dia_ctrl.propertyChanged.connect(self._on_min_dia)
        self.max_dia_ctrl.propertyChanged.connect(self._on_max_dia)
        self.flange_height_ctrl.propertyChanged.connect(self._on_flange_height)
        self.flange_width_ctrl.propertyChanged.connect(self._on_flange_width)
