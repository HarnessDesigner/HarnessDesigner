# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d


class StartStopPosition2DMixin(BaseMixin):
    """Represent a start stop position 2dmixin in :mod:`harness_designer.database.project_db.mixins.start_stop_position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_start_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def start_position2d(self) -> _point.Point:
        """Return the start position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_start_position2d is None:
            point_id = self.start_position2d_id

            self._stored_start_position2d = self._table.db.pjt_points2d_table[point_id]
            point = self._stored_start_position2d.point
        else:
            point = self._stored_start_position2d.point

        if self._obj is not None:
            self._stored_start_position2d.add_object(self._obj())

        return point

    @property
    def start_position2d_id(self) -> int:
        """Return the start position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('start_point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.start_position2d_id = point_id

        return point_id

    @start_position2d_id.setter
    def start_position2d_id(self, value: int):
        """Set the start position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, start_point2d_id=value)
        self._populate('start_position2d_id')

    _stored_stop_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def stop_position2d(self) -> _point.Point:
        """Return the stop position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_stop_position2d is None:
            point_id = self.stop_position2d_id

            self._stored_stop_position2d = self._table.db.pjt_points2d_table[point_id]
            point = self._stored_stop_position2d.point
        else:
            point = self._stored_stop_position2d.point

        if self._obj is not None:
            self._stored_stop_position2d.add_object(self._obj())

        return point

    @property
    def stop_position2d_id(self) -> int:
        """Return the stop position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('stop_point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.stop_position2d_id = point_id

        return point_id

    @stop_position2d_id.setter
    def stop_position2d_id(self, value: int):
        """Set the stop position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, stop_point2d_id=value)
        self._populate('stop_position2d_id')


class StartStopPosition2DControl(_prop_ctrls.Property):
    """Represent a start stop position 2dcontrol in :mod:`harness_designer.database.project_db.mixins.start_stop_position2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`StartStopPosition2DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: StartStopPosition2DMixin = None

        super().__init__(parent, '2D Positions', orientation='vertical')

        self.start_ctrl = _prop_ctrls.Position2DProperty(self, 'Start')
        self.stop_ctrl = _prop_ctrls.Position2DProperty(self, 'Stop')

        self.addWidget(self.start_ctrl)
        self.addWidget(self.stop_ctrl)


    def set_obj(self, db_obj: StartStopPosition2DMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`StartStopPosition2DMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.start_ctrl.SetValue(None)
            self.stop_ctrl.SetValue(None)
        else:

            self.start_ctrl.SetValue(db_obj.start_position2d)
            self.stop_ctrl.SetValue(db_obj.stop_position2d)
