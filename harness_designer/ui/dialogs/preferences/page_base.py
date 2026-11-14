# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Page containers for the Preferences dialog.

Every page, and every group of settings inside one, answers
``apply() -> list[str]``: it writes whatever the user changed to ``Config``
and returns the labels of the changed settings that only take effect after a
restart, so the dialog can tell the user once at the end.
"""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import fields as _fields
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui


class FieldGroup(QtWidgets.QGroupBox):
    """A titled group box with one labelled row per :class:`fields.Field`."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, title: str,
                 fields: list[_fields.Field]):
        super().__init__(title, parent)

        self.fields = fields

        form = QtWidgets.QFormLayout(self)

        for field in fields:
            label = field.label + ':'
            if field.restart:
                label = field.label + ' *:'

            form.addRow(label, field.build(self))

    @_check_types.do
    def apply(self) -> list[str]:
        changed = [field for field in self.fields if field.apply()]

        return [field.label for field in changed if field.restart]


class PreferencesPage(QtWidgets.QWidget):
    """A scrollable column of groups. Add widgets that have an ``apply()``
    with :meth:`add_group` / :meth:`add_item`, then call :meth:`finish`."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, mainframe: "_ui.MainFrame"):
        super().__init__(parent)

        self.mainframe = mainframe
        self._items: list[QtWidgets.QWidget] = []

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        body = QtWidgets.QWidget(scroll)
        self._layout = QtWidgets.QVBoxLayout(body)
        scroll.setWidget(body)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @_check_types.do
    def add_group(self, title: str, fields: list[_fields.Field]) -> FieldGroup:
        group = FieldGroup(self, title, fields)
        self.add_item(group)

        return group

    @_check_types.do
    def add_item(self, item: QtWidgets.QWidget) -> None:
        """Add a widget that has ``apply() -> list[str]``."""
        self._items.append(item)
        self._layout.addWidget(item)

    @_check_types.do
    def add_note(self, text: str) -> None:
        """Add a line of explanation (not a setting)."""
        note = QtWidgets.QLabel(text, self)
        note.setWordWrap(True)
        self._layout.addWidget(note)

    @_check_types.do
    def finish(self) -> None:
        """Call last: pushes the groups to the top of the page."""
        self._layout.addStretch(1)

    @_check_types.do
    def apply(self) -> list[str]:
        restart: list[str] = []

        for item in self._items:
            restart.extend(item.apply())  # NOQA

        return restart


class TabbedPanel(QtWidgets.QWidget):
    """A notebook of pages: one panel the tree shows, with one tab per page.

    The panel always builds every tab, whichever tab the tree asked for, so
    :meth:`set_tab` can be called right after construction.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None):
        super().__init__(parent)

        self._tabs = QtWidgets.QTabWidget(self)
        self._pages: list[PreferencesPage] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

    @_check_types.do
    def add_tab(self, title: str, page: PreferencesPage) -> None:
        self._pages.append(page)
        self._tabs.addTab(page, title)

    @_check_types.do
    def set_tab(self, index: int) -> None:
        self._tabs.setCurrentIndex(index)

    @_check_types.do
    def apply(self) -> list[str]:
        restart: list[str] = []

        for page in self._pages:
            restart.extend(page.apply())

        return restart
