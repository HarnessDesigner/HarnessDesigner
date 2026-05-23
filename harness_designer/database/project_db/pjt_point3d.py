# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point


class PJTPoints3DTable(PJTTableBase):
    """Represent a PJT points 3dtable in :mod:`harness_designer.database.project_db.pjt_point3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_points3d'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import points3d

        return points3d.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import points3d

        points3d.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPoint3D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTPoint3D']
        """
        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint3D(self, db_id, self.project_id)
            yield point

    def __getitem__(self, item) -> "PJTPoint3D":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint3D`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTPoint3D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: float, y: float, z: float) -> "PJTPoint3D":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: float
        :param y: Y-coordinate value.
        :type y: float
        :param z: Z-coordinate value.
        :type z: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTPoint3D`
        """
        db_id = PJTTableBase.insert(self, x=x, y=y, z=z)
        return PJTPoint3D(self, db_id, self.project_id)


class PJTPoint3D(PJTEntryBase):
    """Represent a PJT point 3D in :mod:`harness_designer.database.project_db.pjt_point3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTPoints3DTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'pjt_points3d': [self.db_id],
        }

        return packet

    @property
    def table(self) -> PJTPoints3DTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTPoints3DTable`
        """
        return self._table

    @property
    def x(self) -> float:
        """Return the x.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('x', id=self._db_id)[0][0]

    @x.setter
    def x(self, value: float):
        """Set the x.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, x=value)

    @property
    def y(self) -> float:
        """Return the y.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('y', id=self._db_id)[0][0]

    @y.setter
    def y(self, value: float):
        """Set the y.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, y=value)

    @property
    def z(self) -> float:
        """Return the z.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('z', id=self._db_id)[0][0]

    @z.setter
    def z(self, value: float):
        """Set the z.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, z=value)

    def _update_point(self, point: _point.Point):
        """Update the point.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        x, y, z = point.as_float

        self._table.update(self._db_id, x=x, y=y, z=z)

    _stored_point3d: _point.Point = None

    @property
    def point(self) -> _point.Point:
        """Return the point.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_point3d is None:
            self._stored_point3d = _point.Point(self.x, self.y, self.z, db_id=str(self.db_id) + '3d')
            self._stored_point3d.bind(self._update_point)

        return self._stored_point3d
