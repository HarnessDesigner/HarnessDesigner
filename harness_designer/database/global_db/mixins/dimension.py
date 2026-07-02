# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import uuid
from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin
from ....geometry import point as _point


class DimensionMixin(BaseMixin):
    """Represent a dimension mixin in :mod:`harness_designer.database.global_db.mixins.dimension`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        width, height, length = scale.as_float

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            self._table.update(self._db_id, width=1.0)
            x = 1.0

        if y <= 0:
            self._table.update(self._db_id, height=1.0)
            y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('length', id=self._db_id)[0][0]

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
    def width(self) -> float:
        """Return the width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        """Set the width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, width=value)
        self._populate('width')

    @property
    def height(self) -> float:
        """Return the height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        """Set the height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, height=value)
        self._populate('height')

    @property
    def size(self) -> tuple:
        return self._table.select('width', 'height', 'length', id=self._db_id)[0]

    @size.setter
    def size(self, value: tuple):
        self._table.update(self._db_id, width=value[0], height=value[1], length=value[2])


class DimensionControl(_prop_ctrls.Category):
    """Represent a dimension control in :mod:`harness_designer.database.global_db.mixins.dimension`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`DimensionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: DimensionMixin = None

        super().__init__(parent, 'Dimensions')

        self.length_ctrl = _prop_ctrls.FloatProperty(
            self, 'Length', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.width_ctrl = _prop_ctrls.FloatProperty(
            self, 'Width', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.height_ctrl = _prop_ctrls.FloatProperty(
            self, 'Height', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.addWidget(self.length_ctrl)
        self.addWidget(self.width_ctrl)
        self.addWidget(self.height_ctrl)

        self.length_ctrl.propertyChanged.connect(self._on_length)
        self.width_ctrl.propertyChanged.connect(self._on_width)
        self.height_ctrl.propertyChanged.connect(self._on_height)

    def set_obj(self, db_obj: DimensionMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`DimensionMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.length_ctrl.SetValue(0.0)
            self.width_ctrl.SetValue(0.0)
            self.height_ctrl.SetValue(0.0)
            self.length_ctrl.setEnabled(False)
            self.width_ctrl.setEnabled(False)
            self.height_ctrl.setEnabled(False)
        else:
            self.length_ctrl.SetValue(db_obj.length)
            self.width_ctrl.SetValue(db_obj.width)
            self.height_ctrl.SetValue(db_obj.height)
            self.length_ctrl.setEnabled(True)
            self.width_ctrl.setEnabled(True)
            self.height_ctrl.setEnabled(True)

    def _on_length(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the length event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        self.db_obj.length = evt.GetValue()

    def _on_width(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the width event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        self.db_obj.width = evt.GetValue()

    def _on_height(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the height event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        self.db_obj.height = evt.GetValue()
