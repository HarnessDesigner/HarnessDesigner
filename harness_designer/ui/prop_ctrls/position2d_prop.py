# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import prop_base as _prop_base
from . import float_prop as _float_prop


class Position2DProperty(_prop_base.Property):
    """Represent a position 2dproperty in :mod:`harness_designer.ui.prop_ctrls.position2d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`Position2DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label, orientation='vertical')

        self._position = None
        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=-9999.0, max_value=9999.0, increment=0.01)
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=-9999.0, max_value=9999.0, increment=0.01)

        self._sizer.addWidget(self.x_ctrl)
        self._sizer.addWidget(self.y_ctrl)

        self.x_ctrl.property_changed.connect(self._on_x)
        self.y_ctrl.property_changed.connect(self._on_y)

    def SetValue(self, position):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: UNKNOWN
        """
        self._position = position
        enabled = position is not None
        self.x_ctrl.SetValue(position.x if position else 0.0)
        self.y_ctrl.SetValue(position.y if position else 0.0)
        self.x_ctrl.setEnabled(enabled)
        self.y_ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._position.x = evt.GetValue()

    def _on_y(self, evt):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._position.y = evt.GetValue()
