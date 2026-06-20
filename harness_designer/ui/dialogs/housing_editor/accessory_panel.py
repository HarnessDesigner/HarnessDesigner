# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import housing_obj as _housing_obj
from .... import color as _color
from . import accessory_obj as _accessory_obj
from ...widgets import triple_float_ctrl as _triple_float_ctrl


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor


class AccessoryPanel(QtWidgets.QTabWidget):
    """Represent an accessory panel in :mod:`harness_designer.ui.dialogs.housing_editor.accessory_panel`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, dialog, panel: "_housing_editor.HousingEditorDialog",
                 housing: _housing_obj.Housing3D):
        """Initialise the :class:`AccessoryPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param dialog: Value for ``dialog``.
        :type dialog: UNKNOWN
        :param panel: Value for ``panel``.
        :type panel: :class:`_housing_editor.HousingEditorDialog`
        :param housing: Value for ``housing``.
        :type housing: :class:`_housing_obj.Housing3D`
        """

        super().__init__(panel)

        self.housing = housing
        self.dialog = dialog

        boot_color = _color.Color(1.0, 0.2, 0.2, 1.0)
        boot_pos = housing.db_obj.boot_position3d

        cpa_color = _color.Color(0.2, 1.0, 0.2, 1.0)
        cpa_pos = housing.db_obj.cpa_lock_position3d

        cover_color = _color.Color(0.2, 0.2, 1.0, 1.0)
        cover_pos = housing.db_obj.cover_position3d

        tpa1_color = _color.Color(0.2, 1.0, 1.0, 1.0)
        tpa1_pos = housing.db_obj.tpa_lock_1_position3d

        tpa2_color = _color.Color(1.0, 1.0, 0.2, 1.0)
        tpa2_pos = housing.db_obj.tpa_lock_2_position3d

        seal_color = _color.Color(1.0, 0.2, 1.0, 1.0)
        seal_pos = housing.db_obj.seal_position3d

        self.boot_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, boot_pos, boot_color)

        self.cover_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, cover_pos, cover_color)

        self.cpa_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, cpa_pos, cpa_color)

        self.tpa1_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, tpa1_pos, tpa1_color)

        self.tpa2_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, tpa2_pos, tpa2_color)

        self.seal_ctrl = _triple_float_ctrl.TripleFloatCtrl(
            self, seal_pos, seal_color)

        self.boot_obj = _accessory_obj.HousingAccessory(
            dialog, boot_pos, boot_color)

        self.cover_obj = _accessory_obj.HousingAccessory(
            dialog, cover_pos, cover_color)

        self.cpa_obj = _accessory_obj.HousingAccessory(
            dialog, cpa_pos, cpa_color)

        self.tpa1_obj = _accessory_obj.HousingAccessory(
            dialog, tpa1_pos, tpa1_color)

        self.tpa2_obj = _accessory_obj.HousingAccessory(
            dialog, tpa2_pos, tpa2_color)

        self.seal_obj = _accessory_obj.HousingAccessory(
            dialog, seal_pos, seal_color)

        self.addTab(self.boot_ctrl, 'Boot Position')
        self.addTab(self.cover_ctrl, 'Cover Position')
        self.addTab(self.cpa_ctrl, 'CPA Lock Position')
        self.addTab(self.tpa1_ctrl, 'TPA Lock 1 Position')
        self.addTab(self.tpa2_ctrl, 'TPA Lock 2 Position')
        self.addTab(self.seal_ctrl, 'Seal Position')
