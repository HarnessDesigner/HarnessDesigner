# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Optional

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import cavity_obj as _cavity_obj
from . import analysis_panel as _analysis_panel
from ...widgets import checkbox_ctrl as _checkbox_ctrl
from ...widgets import triple_float_ctrl as _triple_float_ctrl
from ...widgets import editable_tab_ctrl as _editable_tab_ctrl
from ...widgets import list_ctrl as _list_ctrl


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor
    from . import housing_obj as _housing_obj
    from ....database.global_db import cavity as _cavity


class CavityGeneral(QtWidgets.QWidget):

    def __init__(self, parent: "CavityTab", cavity3d: _cavity_obj.Cavity3D):
        self._cavity_tab = parent
        self.cavity3d = cavity3d
        super().__init__(parent)

        outer = QtWidgets.QHBoxLayout()
        left = QtWidgets.QVBoxLayout()

        # ── name row ─────────────────────────────────────────────────────────
        name_row = QtWidgets.QHBoxLayout()
        name_lbl = QtWidgets.QLabel('Name:', self)
        self._name_field = QtWidgets.QLineEdit(cavity3d.name or '', self)
        self._name_ok = QtWidgets.QPushButton('OK', self)
        self._name_ok.setFixedWidth(36)
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_field, 1)
        name_row.addWidget(self._name_ok)
        left.addLayout(name_row)

        # ── is-round ─────────────────────────────────────────────────────────
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

        group = QtWidgets.QGroupBox("Compatible Terminal Sizes")
        group_layout = QtWidgets.QVBoxLayout()

        self.terminal_size_ctrl = _list_ctrl.ListCtrl(
            group, terminal_sizes, item_type=float, unique=True)

        self.terminal_size_ctrl.itemAdded.connect(self.on_size_added)
        self.terminal_size_ctrl.itemChanged.connect(self.on_size_edited)
        self.terminal_size_ctrl.itemRemoved.connect(self.on_size_deleted)

        group_layout.addWidget(self.terminal_size_ctrl)
        group.setLayout(group_layout)
        outer.addWidget(group)

        group = QtWidgets.QGroupBox("Compatible Terminals")
        group_layout = QtWidgets.QVBoxLayout()

        self.compat_terminal_ctrl = _list_ctrl.ListCtrl(
            group, compat_terminals, item_type=str, unique=True)

        self.compat_terminal_ctrl.itemAdded.connect(self.on_terminal_added)
        self.compat_terminal_ctrl.itemChanged.connect(self.on_terminal_edited)
        self.compat_terminal_ctrl.itemRemoved.connect(self.on_terminal_deleted)

        group_layout.addWidget(self.compat_terminal_ctrl)
        group.setLayout(group_layout)
        outer.addWidget(group)

        self.setLayout(outer)

        self._name_ok.clicked.connect(self.on_name_ok)
        self._name_field.returnPressed.connect(self.on_name_ok)

    # ── name ──────────────────────────────────────────────────────────────────

    def on_name_ok(self) -> None:
        new_name = self._name_field.text().strip()
        if not new_name:
            return
        self.cavity3d.name = new_name
        self._cavity_tab.name = new_name
        panel = self._cavity_tab._panel
        idx = panel.indexOf(self._cavity_tab)
        if idx >= 0:
            panel.setTabText(idx, new_name)

    # ── compatible terminals ───────────────────────────────────────────────────

    def on_terminal_added(self, _, part_number):
        self.cavity3d.compat_terminals = self.compat_terminal_ctrl.GetValue()

        for terminal in self.cavity3d.compat_terminals:
            if part_number == terminal.part_number:
                blade_size = terminal.blade_size

                if not blade_size:
                    return

                self.terminal_size_ctrl.add_item(blade_size)
                return

    def on_terminal_edited(self, _, old_value, new_value):
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
        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_size_edited(self, _, old_value, new_value):
        if old_value == new_value:
            return

        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_size_deleted(self, _, __):
        self.cavity3d.terminal_sizes = self.terminal_size_ctrl.GetValue()

    def on_is_round(self):
        value = self.is_round_ctrl.GetValue()
        self.cavity3d.is_round = value


class CavityTab(QtWidgets.QTabWidget):

    def __init__(self, parent: "CavityPanel", cavity: "_cavity.Cavity"):
        super().__init__(parent)

        self._panel = parent   # direct reference to the owning CavityPanel

        self.cavity = _cavity_obj.Cavity(parent.dialog, cavity)
        cavity3d = self.cavity.obj3d

        self.size = cavity3d.scale

        self.size_ctrl = _triple_float_ctrl.TripleFloatCtrl(self, self.size, register_events=False)
        self.general_ctrl = CavityGeneral(self, cavity3d)

        self.size_ctrl.x.value_changed.connect(self.on_size_x)
        self.size_ctrl.y.value_changed.connect(self.on_size_y)
        self.size_ctrl.z.value_changed.connect(self.on_size_z)

        self.addTab(self.general_ctrl, 'General')
        self.addTab(self.size_ctrl, 'Size')

        # Surface indices into MeshSurfacePicker.surfaces; set when committed
        # from analysis.  -1 for cavities loaded from the database.
        self.wire_surf_si: int = -1
        self.term_surf_si: int = -1

    def on_size_x(self, value: float) -> None:
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
        self.size.unbind(self.size_ctrl.on_position_or_angle)
        self.size.z = value
        self.cavity.obj3d.length = value
        self.size.bind(self.size_ctrl.on_position_or_angle)

    def set_selected(self, flag: bool) -> None:
        self.cavity.obj3d.set_selected(flag)

    @property
    def is_selected(self) -> bool:
        return self.cavity.obj3d.is_selected

    @property
    def name(self) -> str:
        return self.cavity.obj3d.name

    @name.setter
    def name(self, value: str):
        self.cavity.obj3d.name = value

    @property
    def index(self) -> int:
        return self.cavity.obj3d.idx

    @index.setter
    def index(self, value: int):
        self.cavity.obj3d.idx = value

    def delete(self):
        self.cavity.delete()


class CavityPanel(_editable_tab_ctrl.EditableTabCtrl):

    rename_tab_label = 'Rename Cavity'
    add_tab_label = None
    delete_tab_label = 'Delete Cavity'

    tab_bar_tooltip = ('Double click tab to rename a cavity or\n'
                       'right click tab to get a list of actions to perform.')

    # Emits (wire_surf_si, term_surf_si) when the active cavity changes.
    # Both are -1 for cavities loaded from the database rather than analyzed
    # in the current session.
    cavitySelected: QtCore.SignalInstance = QtCore.Signal(int, int)

    def __init__(self, dialog, panel: "_housing_editor.HousingEditorDialog",
                 housing: "_housing_obj.Housing3D"):
        super().__init__(panel)

        self.__hold_change = False
        self.cavities: list[CavityTab] = []
        self.housing = housing
        self.dialog = dialog

        self._num_pins = housing.db_obj.num_pins
        self._update_pin_count = self._num_pins == 0

        self.tabDeleteRequested.connect(self.on_cavity_remove)
        self.tabRenamed.connect(self.on_cavity_name_change)

        # Enable drag-to-reorder tabs; tabMoved fires after each drop.
        self.tabBar().setMovable(True)
        self.tabBar().tabMoved.connect(self.on_cavity_moved)
        self.currentChanged.connect(self._on_current_changed)

        for cavity in housing.db_obj.cavities:
            if cavity is None:
                continue

            self.on_add_cavity(cavity.idx, cavity)

    def set_cavity(self, cavity):
        pass

    def on_cavity_remove(self, idx: int, _: str, cavity: CavityTab):
        self.cavities.pop(idx)
        self.removeTab(idx)

        cavity.delete()

        for i, cavity in enumerate(self.cavities):
            cavity.index = i

    def on_cavity_name_change(self, _: int, old_name: str,  # NOQA
                              new_name: str, cavity: CavityTab) -> None:
        cavity.name = new_name
        # Keep the name field in the General tab in sync.
        cavity.general_ctrl._name_field.setText(new_name)

    def on_cavity_moved(self, from_idx: int, to_idx: int) -> None:
        """Update the cavities list and DB indices after a tab drag."""
        cavity = self.cavities.pop(from_idx)
        self.cavities.insert(to_idx, cavity)
        for i, c in enumerate(self.cavities):
            c.index = i

    def _on_current_changed(self, index: int) -> None:
        if 0 <= index < len(self.cavities):
            ct = self.cavities[index]
            self.cavitySelected.emit(ct.wire_surf_si, ct.term_surf_si)
        else:
            self.cavitySelected.emit(-1, -1)

    def on_add_cavity(self, idx, cavity=None):
        """Add a cavity tab.  ``idx`` is 0-based (matches db ``cavity.idx``).
        Returns the new :class:`CavityTab`, or ``None`` if the pin-count limit
        was reached.
        """
        db_idx = idx       # keep 0-based for DB storage
        idx += 1           # 1-based for display label and pin-count comparison

        if cavity is None:
            has_name = False
            name = str(idx)
        else:
            name = cavity.name
            if not name:
                name = str(idx)
                cavity.name = str(idx)

            has_name = True

        housing_id = self.housing.db_obj.db_id
        cavities_table = self.housing.db_obj.table.db.cavities_table

        num_pins = self._num_pins

        if self._update_pin_count:
            self.housing.db_obj.num_pins += 1
            self._num_pins += 1
            num_pins += 1

        cavity_tab = None

        if idx <= num_pins:   # was strict < — must use <= to allow the Nth pin
            if cavity is None:
                cavity = cavities_table.insert(housing_id, db_idx)

            if not has_name:
                cavity.name = name

            cavity_tab = CavityTab(self, cavity)
            self.addTab(cavity_tab, name)

            if not has_name:
                for c in self.cavities:
                    if c.is_selected:
                        c.set_selected(False)
                        break

                cavity_tab.set_selected(True)

            self.cavities.append(cavity_tab)

        return cavity_tab

    def commit_cavity(self, idx: int, item: '_analysis_panel.AnalysisItem') -> None:
        """Commit one analysis result to the DB and create its tab.
        ``idx`` is 0-based (the next free index after existing cavities).
        """
        cavity_tab = self.on_add_cavity(idx)
        if cavity_tab is None:
            return

        cavity_tab.cavity.obj3d.apply_analysis(
            item.kind, item.params, item.d_start, item.d_end)

        # Store the surface indices so the overlay can highlight them when
        # this cavity tab is selected.
        cavity_tab.wire_surf_si = item.wire_surf_si
        cavity_tab.term_surf_si = item.term_surf_si

        if item.name:
            cavity_tab.name = item.name
            self.setTabText(self.indexOf(cavity_tab), item.name)
            cavity_tab.general_ctrl._name_field.setText(item.name)
