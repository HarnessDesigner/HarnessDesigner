# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QTabWidget
)
import random

from . import cavity_obj as _cavity_obj
from ...widgets import checkbox_ctrl as _checkbox_ctrl
from . import triple_float_ctrl as _triple_float_ctrl
from ...widgets import editable_tab_ctrl as _editable_tab_ctrl
from ...widgets import list_ctrl as _list_ctrl
from .... import color as _color


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor
    from . import housing_obj as _housing_obj
    from ....database.global_db import cavity as _cavity


class CavityGeneral(QWidget):
    """Represent a cavity general in :mod:`harness_designer.ui.dialogs.housing_editor.cavity_panel`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "CavityTab", cavity3d: _cavity_obj.Cavity3D):
        """Initialise the :class:`CavityGeneral` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`CavityTab`
        :param cavity3d: Value for ``cavity3d``.
        :type cavity3d: :class:`_cavity_obj.Cavity3D`
        """
        self.cavity3d = cavity3d
        super().__init__(parent)

        outer = QHBoxLayout()
        left = QVBoxLayout()

        self.is_round_ctrl = _checkbox_ctrl.CheckboxCtrl(self, 'Is Round:')
        self.is_round_ctrl.SetValue(cavity3d.is_round)
        self.is_round_ctrl.checkStateChanged.connect(
            lambda _: self.on_is_round())

        left.addWidget(self.is_round_ctrl)
        left.addStretch(1)
        outer.addLayout(left)

        terminal_sizes = cavity3d.terminal_sizes
        compat_terminals = []

        for terminal in cavity3d.compat_terminals:
            blade_size = terminal.blade_size
            if blade_size not in terminal_sizes:
                terminal_sizes.append(blade_size)

            compat_terminals.append(terminal.part_number)

        group = QGroupBox("Compatible Terminal Sizes")
        group_layout = QVBoxLayout()

        self.terminal_size_ctrl = _list_ctrl.ListCtrl(
            group, terminal_sizes, item_type=float, unique=True)

        self.terminal_size_ctrl.itemAdded.connect(self.on_size_added)
        self.terminal_size_ctrl.itemChanged.connect(self.on_size_edited)
        self.terminal_size_ctrl.itemRemoved.connect(self.on_size_deleted)

        group_layout.addWidget(self.terminal_size_ctrl)
        group.setLayout(group_layout)
        outer.addWidget(group)

        group = QGroupBox("Compatible Terminals")
        group_layout = QVBoxLayout()

        self.compat_terminal_ctrl = _list_ctrl.ListCtrl(
            group, compat_terminals, item_type=str, unique=True)

        self.compat_terminal_ctrl.itemAdded.connect(self.on_terminal_added)
        self.compat_terminal_ctrl.itemChanged.connect(self.on_terminal_edited)
        self.compat_terminal_ctrl.itemRemoved.connect(self.on_terminal_deleted)

        group_layout.addWidget(self.compat_terminal_ctrl)
        group.setLayout(group_layout)
        outer.addWidget(group)

        self.setLayout(outer)

    def on_terminal_added(self, _, part_number):
        """Handle the terminal added event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param part_number: Value for ``part_number``.
        :type part_number: UNKNOWN
        """
        self.cavity3d.compat_terminals = self.compat_terminal_ctrl.GetValue()

        for terminal in self.cavity3d.compat_terminals:
            if part_number == terminal.part_number:
                blade_size = terminal.blade_size

                if not blade_size:
                    return

                self.terminal_size_ctrl.add_item(blade_size)
                return

    def on_terminal_edited(self, _, old_value, new_value):
        """Handle the terminal edited event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param old_value: Value for ``old_value``.
        :type old_value: UNKNOWN
        :param new_value: Value for ``new_value``.
        :type new_value: UNKNOWN
        """
        if old_value == new_value:
            return

        old_blade_size = 0.0

        for terminal in self.cavity3d.compat_terminals:
            if terminal.part_number == old_value:
                old_blade_size = terminal.blade_size
                break

        self.cavity3d.compat_terminals = self.compat_terminal_ctrl.GetValue()

        compat_terminals = self.cavity3d.compat_terminals
        terminal_sizes = self.terminal_size_ctrl.GetValue()

        if old_blade_size:
            terminal_size_matches = 0

            for terminal in compat_terminals:
                if terminal.blade_size == old_blade_size:
                    terminal_size_matches += 1

            if terminal_size_matches == 0:
                if old_blade_size in terminal_sizes:
                    terminal_sizes.remove(old_blade_size)

        for terminal in compat_terminals:
            if terminal.part_number == new_value:
                blade_size = terminal.blade_size
                if blade_size and blade_size not in terminal_sizes:
                    terminal_sizes.append(blade_size)

                break

        self.terminal_size_ctrl.clear()
        for blade_size in terminal_sizes:
            self.terminal_size_ctrl.add_item(blade_size)

    def on_terminal_deleted(self, _, part_number):
        """Handle the terminal deleted event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param part_number: Value for ``part_number``.
        :type part_number: UNKNOWN
        """

        compat_terminals = self.cavity3d.compat_terminals

        blade_size = 0.0

        for terminal in compat_terminals:
            if terminal.part_number == part_number:
                blade_size = terminal.blade_size
                break

        self.cavity3d.compat_terminals = self.compat_terminal_ctrl.GetValue()

        if blade_size:
            terminal_size_matches = 0

            for terminal in compat_terminals:
                if terminal.blade_size == blade_size:
                    terminal_size_matches += 1

            terminal_sizes = self.terminal_size_ctrl.GetValue()

            if (
                terminal_size_matches == 0 and
                blade_size in terminal_sizes
            ):
                terminal_sizes.remove(blade_size)

                self.terminal_size_ctrl.clear()
                for blade_size in terminal_sizes:
                    self.terminal_size_ctrl.add_item(blade_size)

    def on_size_added(self, _, __):
        """Handle the size added event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_size_edited(self, _, old_value, new_value):
        """Handle the size edited event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param old_value: Value for ``old_value``.
        :type old_value: UNKNOWN
        :param new_value: Value for ``new_value``.
        :type new_value: UNKNOWN
        """
        if old_value == new_value:
            return

        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_size_deleted(self, _, __):
        """Handle the size deleted event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_is_round(self):
        """Handle the is round event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        value = self.is_round_ctrl.GetValue()
        self.cavity3d.is_round = value


class CavityTab(QTabWidget):
    """Represent a cavity tab in :mod:`harness_designer.ui.dialogs.housing_editor.cavity_panel`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "CavityPanel", cavity: "_cavity.Cavity"):
        """Initialise the :class:`CavityTab` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`CavityPanel`
        :param cavity: Value for ``cavity``.
        :type cavity: :class:`_cavity.Cavity`
        """
        super().__init__(parent)

        color = [random.randrange(10, 255) / 255.0 for _ in range(3)]
        color.append(1.0)

        color = _color.Color(*color)

        self.cavity = _cavity_obj.Cavity(parent.dialog, cavity)
        cavity3d = self.cavity.obj3d

        self.position = cavity3d.position
        self.angle = cavity3d.angle
        self.size = cavity3d.scale

        self.position_ctrl = _triple_float_ctrl.TripleFloatCtrl(self, self.position, color)
        self.angle_ctrl = _triple_float_ctrl.TripleFloatCtrl(self, self.angle, color)
        self.size_ctrl = _triple_float_ctrl.TripleFloatCtrl(self, self.size, color, register_events=False)
        self.general_ctrl = CavityGeneral(self, cavity3d)

        self.size_ctrl.x.value_changed.connect(self.on_size_x)
        self.size_ctrl.y.value_changed.connect(self.on_size_y)
        self.size_ctrl.z.value_changed.connect(self.on_size_z)

        self.addTab(self.general_ctrl, 'General')
        self.addTab(self.position_ctrl, 'Position')
        self.addTab(self.angle_ctrl, 'Angle')
        self.addTab(self.size_ctrl, 'Size')

    def on_size_x(self, value: float) -> None:
        """Handle the size x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.size.unbind(self.size_ctrl.on_position_or_angle)
        self.size.x = value
        self.cavity.obj3d.width = value

        if self.cavity.obj3d.is_round:
            self.size.y = value
            self.cavity.obj3d.height = value
            self.size_ctrl.y.SetValue(value)
            self.size_ctrl.y.update()

        self.size.bind(self.size_ctrl.on_position_or_angle)

    def on_size_y(self, value: float) -> None:
        """Handle the size y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.size.unbind(self.size_ctrl.on_position_or_angle)
        self.size.y = value
        self.cavity.obj3d.height = value

        if self.cavity.obj3d.is_round:
            self.size.x = value
            self.cavity.obj3d.width = value
            self.size_ctrl.x.SetValue(value)
            self.size_ctrl.x.update()

        self.size.bind(self.size_ctrl.on_position_or_angle)

    def on_size_z(self, value: float) -> None:
        """Handle the size z event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.size.unbind(self.size_ctrl.on_position_or_angle)
        self.size.z = value
        self.cavity.obj3d.length = value
        self.size.bind(self.size_ctrl.on_position_or_angle)

    def set_selected(self, flag: bool) -> None:
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.cavity.obj3d.set_selected(flag)

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self.cavity.obj3d.is_selected

    @property
    def name(self) -> str:
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self.cavity.obj3d.name

    @name.setter
    def name(self, value: str):
        """Set the name.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self.cavity.obj3d.name = value

    @property
    def index(self) -> int:
        """Return the index.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self.cavity.obj3d.idx

    @index.setter
    def index(self, value: int):
        """Set the index.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self.cavity.obj3d.idx = value

    def delete(self):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.cavity.delete()


class CavityPanel(_editable_tab_ctrl.EditableTabCtrl):
    """Represent a cavity panel in :mod:`harness_designer.ui.dialogs.housing_editor.cavity_panel`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    rename_tab_label = 'Rename Cavity'
    add_tab_label = 'Add Cavity'
    delete_tab_label = 'Delete Cavity'

    # override this attribute to set a custom tooltip for the tab bar
    tab_bar_tooltip = ('Double click tab to rename a cavity or\n'
                       'right click tab to get a list of actions to perform.')

    def __init__(self, dialog, panel: "_housing_editor.HousingEditorDialog",
                 housing: "_housing_obj.Housing3D"):
        """Initialise the :class:`CavityPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param dialog: Value for ``dialog``.
        :type dialog: UNKNOWN
        :param panel: Value for ``panel``.
        :type panel: :class:`_housing_editor.HousingEditorDialog`
        :param housing: Value for ``housing``.
        :type housing: :class:`_housing_obj.Housing3D`
        """

        super().__init__(panel)

        self.__hold_change = False
        self.cavities: list[CavityTab] = []

        for cavity in housing.db_obj.cavities:
            if cavity is None:
                continue

            self.on_add_cavity(cavity.idx - 1, cavity)

        self.housing = housing
        self.dialog = dialog

        if not self.cavities:
            self.dialog.housing_panel.enable_housing_ctrls(True)

    def on_cavity_remove(self, idx: int, _: str, cavity: CavityTab):
        """Handle the cavity remove event.

        UNKNOWN details are inferred from the callable name and signature.

        :param idx: Value for ``idx``.
        :type idx: int
        :param _: Value for ``_``.
        :type _: str
        :param cavity: Value for ``cavity``.
        :type cavity: :class:`CavityTab`
        """
        self.cavities.pop(idx)
        self.removeTab(idx)

        cavity.delete()

        for i, cavity in enumerate(self.cavities):
            cavity.index = i + 1

    def on_cavity_name_change(self, _: int, old_name: str,  # NOQA
                              new_name: str, cavity: CavityTab) -> None:
        """Handle the cavity name change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: int
        :param old_name: Value for ``old_name``.
        :type old_name: str
        :param new_name: Value for ``new_name``.
        :type new_name: str
        :param cavity: Value for ``cavity``.
        :type cavity: :class:`CavityTab`
        """

        if new_name == old_name:
            return

        cavity.name = new_name

    def on_add_cavity(self, idx, cavity=None):
        """Handle the add cavity event.

        UNKNOWN details are inferred from the callable name and signature.

        :param idx: Value for ``idx``.
        :type idx: UNKNOWN
        :param cavity: Value for ``cavity``.
        :type cavity: UNKNOWN
        """
        idx += 1

        if cavity is None:
            has_name = False
            name = str(idx)
        else:
            name = cavity.name
            has_name = True

        housing_id = self.housing.db_obj.db_id
        num_pins = self.housing.db_obj.num_pins
        cavities_table = self.housing.db_obj.table.db.cavities_table

        if (num_pins > 0 and idx <= num_pins) or num_pins == 0:
            if cavity is None:
                cavity = cavities_table.insert(housing_id, idx)

            if not has_name:
                cavity.name = name

            cavity_tab = CavityTab(self, cavity)
            self.addTab(cavity_tab, name)

            if not self.cavities:
                self.dialog.housing_panel.enable_housing_ctrls(False)

            if not has_name:
                for c in self.cavities:
                    if c.is_selected:
                        c.set_selected(False)
                        break

                cavity_tab.set_selected(True)

            self.cavities.append(cavity_tab)
