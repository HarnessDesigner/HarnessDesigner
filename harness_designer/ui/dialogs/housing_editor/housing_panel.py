# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget

from . import housing_obj as _housing_obj
from . import triple_float_ctrl as _triple_float_ctrl


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor


class HousingPanel(QTabWidget):

    def __init__(self, dialog, panel: "_housing_editor.HousingEditorDialog",
                 housing: _housing_obj.Housing3D):

        QTabWidget.__init__(self, panel)

        self.housing = housing
        self.dialog = dialog

        self.housing_angle = housing.angle
        self.housing_position = housing.position

        self.housing_angle_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, self.housing_angle)

        self.housing_position_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, self.housing_position)

        tip = 'You need to remove all added cavities in order to rotate the housing'
        self.housing_angle_ctrl.setEnabled(False)
        self.housing_angle_ctrl.setToolTip(tip)

        tip = 'You need to remove all added cavities in order to position the housing'
        self.housing_position_ctrl.setEnabled(False)
        self.housing_position_ctrl.setToolTip(tip)

        self.addTab(self.housing_angle_ctrl, 'Angle')
        self.addTab(self.housing_position_ctrl, 'Position')

        self.enable_housing_ctrls(True)

    def enable_housing_ctrls(self, flag: bool):
        if flag:
            angle_tip = ''
            position_tip = ''
        else:
            angle_tip = 'You need to remove all added cavities in order to rotate the housing'
            position_tip = 'You need to remove all added cavities in order to position the housing'

        self.housing_angle_ctrl.setEnabled(flag)
        self.housing_angle_ctrl.setToolTip(angle_tip)

        self.housing_position_ctrl.setEnabled(flag)
        self.housing_position_ctrl.setToolTip(position_tip)
