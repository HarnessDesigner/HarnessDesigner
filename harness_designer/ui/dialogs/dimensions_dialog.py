# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Prompt for a catalog part's length/width/height when the catalog
data leaves one or more of them at 0.0.

A 0.0 dimension isn't just a display quirk -- ``objects.objects_3d.*``
placeholder geometry (and, for a terminal with no model yet, the
initial floating-preview box) scales its VBO directly off these three
values, so a 0.0 collapses that axis to nothing and the object is
effectively invisible until (if ever) a real 3D model replaces the
placeholder. :func:`ensure_dimensions` is meant to be called from every
``start_add`` classmethod right after the user picks a catalog part,
before any project row gets created for it.
"""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QDialog

from . import dialog_base as _dialog_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ...database.global_db.mixins.dimension import DimensionMixin
    from ...database.global_db.mixins.resource import ResourceMixin


@_check_types.do
def _open_local_path(path: str) -> None:
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))


@_check_types.do
def _open_resource(part: "ResourceMixin", kind: str) -> None:
    """Open *part*'s linked datasheet/CAD file (*kind* is ``'datasheet'``
    or ``'cad'``) with the OS default handler, downloading it first if
    it's linked in the catalog but not yet cached locally.
    """
    resource_id = getattr(part, f'{kind}_id')
    if resource_id is None:
        return

    resource = getattr(part.table.db, f'{kind}s_table')[resource_id]

    path = resource.data_path
    if path is not None:
        _open_local_path(path)
        return

    @_check_types.do
    def _on_loaded(*_args, **_kwargs):
        loaded_path = resource.data_path
        if loaded_path is not None:
            _open_local_path(loaded_path)

    resource.load(part.manufacturer.name, part.part_number, _on_loaded)


class _DimensionField(QtWidgets.QLineEdit):
    """Plain numeric text entry for one length/width/height field.

    A ``QDoubleSpinBox`` (used everywhere else in the app for a
    dimension) always displays a real, already-committed numeric
    value -- there's no way for it to sit genuinely empty. This dialog
    needs exactly that: a *suggested* (unconfirmed, parsed-from-text)
    value has to be visibly different from one the user actually
    entered, and a plain ``QLineEdit`` with native placeholder text is
    the direct way to get that -- ghosted, not counted as "entered",
    until the user types over it or explicitly accepts it.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setValidator(QtGui.QDoubleValidator(0.0, 999999.0, 6, self))

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Right arrow, with the field still empty, accepts whatever's
        showing as the placeholder and moves on to the next field --
        the same "accept the suggestion" gesture a browser address bar
        autocomplete uses, extended to also advance focus the way
        pressing Tab would.
        """
        if (
            event.key() == QtCore.Qt.Key.Key_Right and
            not self.text() and self.placeholderText()
        ):
            self.setText(self.placeholderText())
            self.focusNextChild()
            return

        super().keyPressEvent(event)

    @_check_types.do
    def value(self) -> float | None:
        """The field's own entered value, or None if it's empty/not a
        valid number -- a shown placeholder never counts.
        """
        text = self.text().strip()
        if not text:
            return None

        try:
            return float(text)
        except ValueError:
            return None


class DimensionsDialog(_dialog_base.BaseDialog):
    """Modal length/width/height entry for one catalog part -- see the
    module docstring.
    """

    @_check_types.do
    def __init__(
        self, parent: "_ui.MainFrame", part: "DimensionMixin", part_number: str,
        suggested: dict | None = None
    ):
        super().__init__(parent, title=f'Missing Dimensions -- {part_number}', size=(380, 260))

        suggested = suggested or {}

        layout = QtWidgets.QVBoxLayout(self.panel)

        message = (
            f'{part_number!r} is missing one or more physical dimensions in '
            f'the catalog. Enter its real length, width, and height before '
            f'adding it to the project.')

        if suggested:
            message += (
                ' A value parsed from the part\'s own catalog description '
                'is shown as a placeholder in the field(s) below -- press '
                'the Right arrow key with the field empty to accept it, or '
                'type a real value instead.')

        label = QtWidgets.QLabel(message, self.panel)
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QtWidgets.QFormLayout()

        self.length_field = _DimensionField(self.panel)
        self.width_field = _DimensionField(self.panel)
        self.height_field = _DimensionField(self.panel)

        # A field already covered by a trusted estimate (see
        # ensure_dimensions -- applied to *part* before this dialog is
        # ever constructed) shows that real, already-committed value;
        # one *suggested* (unconfirmed) instead shows it as a
        # placeholder only; one with neither starts genuinely empty.
        for name, field in (
            ('length', self.length_field), ('width', self.width_field),
            ('height', self.height_field)
        ):
            current = getattr(part, name)
            if current > 0.0:
                field.setText(f'{current:g}')
            elif name in suggested:
                field.setPlaceholderText(f'{suggested[name]:g}')

            field.textChanged.connect(self._update_ok_enabled)

        form.addRow('Length (mm):', self.length_field)
        form.addRow('Width (mm):', self.width_field)
        form.addRow('Height (mm):', self.height_field)

        layout.addLayout(form)

        # Reference material for filling in the fields above -- disabled
        # outright when this part has no linked row in the catalog at
        # all (nothing to open), regardless of whether it's been
        # downloaded/cached to a local file yet.
        resource_row = QtWidgets.QHBoxLayout()

        datasheet_btn = QtWidgets.QPushButton('Open Datasheet', self.panel)
        datasheet_btn.setEnabled(getattr(part, 'datasheet_id', None) is not None)
        datasheet_btn.clicked.connect(lambda: _open_resource(part, 'datasheet'))
        resource_row.addWidget(datasheet_btn)

        cad_btn = QtWidgets.QPushButton('Open CAD', self.panel)
        cad_btn.setEnabled(getattr(part, 'cad_id', None) is not None)
        cad_btn.clicked.connect(lambda: _open_resource(part, 'cad'))
        resource_row.addWidget(cad_btn)

        layout.addLayout(resource_row)
        layout.addStretch(1)

        # OK stays disabled (Cancel is always available -- BaseDialog
        # never disables it) until every field actually holds an
        # entered, non-zero value -- a still-shown placeholder must
        # not silently count as "entered".
        self._ok_button = self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self._update_ok_enabled()

    @_check_types.do
    def _update_ok_enabled(self, *_args) -> None:
        valid = all(
            field.value() is not None and field.value() > 0.0
            for field in (self.length_field, self.width_field, self.height_field))

        self._ok_button.setEnabled(valid)


@_check_types.do
def ensure_dimensions(
    mainframe: "_ui.MainFrame", part: "DimensionMixin", part_number: str,
    estimates: dict | None = None, suggested: dict | None = None
) -> bool:
    """Prompt for length/width/height if *part* has any at 0.0.

    *estimates* (optional ``{'length'|'width'|'height': value}``, e.g.
    from ``handlers.terminal_handler.estimate_dimensions``) is applied
    first, silently, to whichever of those fields is currently 0.0 --
    if that alone clears every dimension AND *suggested* is empty, the
    dialog never opens at all.

    *suggested* (same shape) is never applied silently, no matter what
    -- it's a guess (e.g. a value parsed out of free-text catalog
    description text), not a value already trusted in the catalog like
    *estimates* is. Its presence forces the dialog open even if
    *estimates* alone already cleared every dimension, showing the
    guessed field(s) as a placeholder the user still has to look at and
    either accept (Right arrow) or type over -- responsibility for what
    actually lands in the catalog stays with the user, regardless of
    how the guess was arrived at.

    Returns True to proceed with adding *part* (nothing was missing
    and there was nothing to confirm, or the user filled in/confirmed
    the rest); False if the user cancelled, in which case the caller
    should abort its own add flow the same way it would a cancelled
    part-search dialog.

    Values are written straight to *part*'s own catalog row (see
    ``DimensionMixin``'s own setters) -- fixing a part here fixes it
    for every future placement, not just this one, and for every view
    (3D/schematic/pegboard) that reads the same part.
    """
    if estimates:
        for field, value in estimates.items():
            if getattr(part, field) <= 0.0:
                setattr(part, field, value)

    if not suggested and part.length > 0.0 and part.width > 0.0 and part.height > 0.0:
        return True

    dlg = DimensionsDialog(mainframe, part, part_number, suggested)
    try:
        accepted = dlg.exec() == QDialog.DialogCode.Accepted

        if accepted:
            # The OK button only enables once every field holds a real
            # entered value (see DimensionsDialog._update_ok_enabled),
            # so these are never None/0.0 here.
            part.length = dlg.length_field.value()
            part.width = dlg.width_field.value()
            part.height = dlg.height_field.value()

            # Now a user-confirmed value, not a guess -- fold it back
            # into blade_size (same width == height == blade_size
            # convention estimate_dimensions itself reads elsewhere)
            # if this part never had one recorded at all.
            if (
                suggested and 'width' in suggested and
                getattr(part, 'blade_size', 0.0) <= 0.0
            ):
                part.blade_size = part.width

        return accepted
    finally:
        dlg.deleteLater()
