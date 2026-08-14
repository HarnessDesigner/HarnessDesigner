# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from ....geometry import point as _point
from .. import pjt_point_pegboard as _pjt_point_pegboard
from .... import check_types as _check_types


class StartStopPositionPegboardMixin(BaseMixin):
    """Represent a start stop position pegboard mixin in :mod:`harness_designer.database.project_db.mixins.start_stop_position_pegboard`.

    Mirrors :class:`~harness_designer.database.project_db.mixins.
    start_stop_position3d.StartStopPosition3DMixin` exactly -- a wire/
    bundle's peg-board start and stop, both always populated (auto-created
    on first ``NULL`` access, same as every other start/stop position),
    never mutually exclusive with anything else the way the wire-layout/
    bundle-layout position columns are.
    """

    _stored_start_position_pegboard: "_pjt_point_pegboard.PJTPointPegboard | DefaultStoredValueType | None" = DefaultStoredValue

    @property
    @_check_types.do
    def start_position_pegboard(self) -> _point.Point:
        """Return the start peg-board position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_start_position_pegboard is DefaultStoredValue:
            point_id = self.start_position_pegboard_id

            if point_id is None:
                self._stored_start_position_pegboard = None
            else:
                self._stored_start_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_start_position_pegboard is not None:
            if self._obj is not None:
                self._stored_start_position_pegboard.add_object(self._obj())

            point = self._stored_start_position_pegboard.point
        else:
            point = None

        return point

    _stored_start_position_pegboard_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def start_position_pegboard_id(self) -> bytes:
        """Return the start peg-board position's row id.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """

        if self._stored_start_position_pegboard_id is DefaultStoredValue:
            point_id = self._table.select('start_point_pegboard_id', id=self._db_id)[0][0]
            if point_id is None:
                point = self._table.db.pjt_points_pegboard_table.insert(x=0.0, y=0.0, z=0.0)
                point_id = point.db_id
                self._table.update(self._db_id, start_point_pegboard_id=point_id)
            self._stored_start_position_pegboard_id = point_id

        return self._stored_start_position_pegboard_id

    @start_position_pegboard_id.setter
    @_check_types.do
    def start_position_pegboard_id(self, value: bytes):
        """Set the start peg-board position's row id.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """

        self._stored_start_position_pegboard_id = value
        self._stored_start_position_pegboard = DefaultStoredValue

        self._table.update(self._db_id, start_point_pegboard_id=value)
        self._populate('start_position_pegboard_id')

    _stored_stop_position_pegboard: "_pjt_point_pegboard.PJTPointPegboard | DefaultStoredValueType | None" = DefaultStoredValue

    @property
    @_check_types.do
    def stop_position_pegboard(self) -> _point.Point:
        """Return the stop peg-board position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_stop_position_pegboard is DefaultStoredValue:
            point_id = self.stop_position_pegboard_id

            if point_id is None:
                self._stored_stop_position_pegboard = None
            else:
                self._stored_stop_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_stop_position_pegboard is not None:
            if self._obj is not None:
                self._stored_stop_position_pegboard.add_object(self._obj())

            point = self._stored_stop_position_pegboard.point
        else:
            point = None

        return point

    _stored_stop_position_pegboard_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def stop_position_pegboard_id(self) -> bytes:
        """Return the stop peg-board position's row id.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """

        if self._stored_stop_position_pegboard_id is DefaultStoredValue:
            point_id = self._table.select('stop_point_pegboard_id', id=self._db_id)[0][0]
            if point_id is None:
                point = self._table.db.pjt_points_pegboard_table.insert(x=0.0, y=0.0, z=0.0)
                point_id = point.db_id
                self._table.update(self._db_id, stop_point_pegboard_id=point_id)

            self._stored_stop_position_pegboard_id = point_id

        return self._stored_stop_position_pegboard_id

    @stop_position_pegboard_id.setter
    @_check_types.do
    def stop_position_pegboard_id(self, value: bytes):
        """Set the stop peg-board position's row id.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """

        self._stored_stop_position_pegboard_id = value
        self._stored_stop_position_pegboard = DefaultStoredValue

        self._table.update(self._db_id, stop_point_pegboard_id=value)
        self._populate('stop_position_pegboard_id')


class StartStopPositionPegboardControl(_prop_ctrls.Property):
    """Represent a start stop position pegboard control in :mod:`harness_designer.database.project_db.mixins.start_stop_position_pegboard`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`StartStopPositionPegboardControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: StartStopPositionPegboardMixin | None = None

        super().__init__(parent, 'Peg-board Positions', orientation='vertical')

        self.start_ctrl = _prop_ctrls.Position3DProperty(self, 'Start')
        self.stop_ctrl = _prop_ctrls.Position3DProperty(self, 'Stop')

        self.addWidget(self.start_ctrl)
        self.addWidget(self.stop_ctrl)

    @_check_types.do
    def set_obj(self, db_obj: StartStopPositionPegboardMixin | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`StartStopPositionPegboardMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.start_ctrl.SetValue(None)
            self.stop_ctrl.SetValue(None)
        else:

            self.start_ctrl.SetValue(db_obj.start_position_pegboard)
            self.stop_ctrl.SetValue(db_obj.stop_position_pegboard)
