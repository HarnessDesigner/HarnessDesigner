# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared callback implementations for the 3d editor object context menus.

The imports of the ui and handler packages are done lazily inside the
functions because this module is imported while the :mod:`objects` package
is still initialising.
"""

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer

from ... import color as _color
from ... import config as _config
from ...gl import materials as _materials
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import base_3d as _base_3d


_colors_config = _config.Config.colors


@_check_types.do
def select_object(obj3d: "_base_3d.Base3D"):
    """Make the object the active selection in all of the editors."""
    select_object_for_object(obj3d.mainframe, obj3d.parent)


@_check_types.do
def select_object_for_object(mainframe, parent):
    """Make ``parent`` the active selection in all of the editors.

    Split out from :func:`select_object` so callers that only hold the
    :class:`ObjectBase` wrapper (e.g. the object browser tree, which never
    touches ``obj3d``) can drive the same deselect-old/select-new sequence.
    """
    current = mainframe.get_selected()

    if current is not None and current is not parent:
        current.set_selected(False)

    parent.set_selected(True)


@_check_types.do
def clone_object(obj3d: "_base_3d.Base3D"):
    """Arm clone mode using the object as the template."""
    mainframe = obj3d.mainframe

    mainframe.editor3d.editor.setCursor(Qt.CursorShape.CrossCursor)
    mainframe.set_clone_obj(obj3d.parent)


@_check_types.do
def delete_object(obj3d: "_base_3d.Base3D"):
    """Remove the object from the editors, the project and the database.

    :param obj3d: 3d object whose parent is being deleted.
    """
    parent = obj3d.parent
    mainframe = obj3d.mainframe

    if mainframe.get_selected() is parent:
        parent.set_selected(False)

    parent.delete()


@_check_types.do
def show_properties(obj3d: "_base_3d.Base3D"):
    """Open the modeless properties dialog for the object.

    The dialog gets its own instance of the object's property tab widget so
    it never competes with the object editor dock, which keeps showing the
    selected object through the table's singleton control. Because the
    dialog is modeless the user can keep working in the editors (camera,
    selection, object editor tabs) while it is open, and any value changes
    apply to the 3d object in real time.
    """
    show_properties_for_object(obj3d.mainframe, obj3d.parent)


@_check_types.do
def show_properties_for_object(mainframe, parent):
    """Open the modeless properties dialog for the ``parent`` wrapper object.

    Split out from :func:`show_properties` so callers that only hold the
    :class:`ObjectBase` wrapper (e.g. the object browser tree, which never
    touches ``obj3d``) can open the same dialog.
    """
    from ...ui.dialogs import properties_dialog as _properties_dialog

    db_obj = parent.db_obj

    if db_obj is None:
        return

    try:
        # objects that support the properties dialog have a matching
        # object editor control registered on their table
        control_cls = type(db_obj.table.control)
    except (AttributeError, RuntimeError):
        return

    tab_widget = control_cls(None)

    # "WireServiceLoop" -> "Wire Service Loop", "CPALock" -> "CPA Lock"
    name = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ',
                  type(parent).__name__)

    dlg = _properties_dialog.PropertiesDialog(
        mainframe, name + ' Properties', tab_widget, db_obj)

    @_check_types.do
    def _cleanup(*_):
        # release the db object so the live position/angle callbacks bound
        # by the property controls do not outlive the dialog
        tab_widget.set_obj(None)
        dlg.deleteLater()

    dlg.finished.connect(_cleanup)
    dlg.show()


@_check_types.do
def start_handler(mainframe, handler_factory):
    """Install an interactive placement handler once the menu has closed.

    The factory may open a modal part-search dialog, so creation is deferred
    until the context menu has finished closing.
    """
    @_check_types.do
    def _do():
        handler = handler_factory()
        if handler is None or handler.is_finalized:
            return

        mainframe.set_obj_handler(handler)

    QTimer.singleShot(0, _do)


@_check_types.do
def run_attached_handler(handler_factory):
    """Run a placement handler whose target object is already known.

    Used for the housing/terminal "Add Seal/CPA/TPA/Cover" style actions
    where the handler attaches the new part as soon as it is constructed and
    no further mouse interaction is required.
    """
    @_check_types.do
    def _do():
        handler = handler_factory()
        if handler.is_finalized or handler.obj is None:
            return

        handler.obj.identify(None)
        handler.capture_position(handler.obj.db_obj.position3d)
        handler.release_capture()

    QTimer.singleShot(0, _do)


@_check_types.do
def get_part_id(mainframe, page_name: str, table, title: str,
                initial_params=None) -> bytes | None:
    """Resolve a part id from the database editor's current selection or a
    part search dialog.

    :param mainframe: Main application frame.
    :param page_name: Attribute name of the page on the database editor,
        e.g. ``'wires'`` or ``'terminals'``.
    :param table: Global database table searched by the dialog.
    :param title: Title for the search dialog.
    :param initial_params: Optional ``part_search.SearchParameters``
        (e.g. via ``SearchParameters.from_part_numbers(compat_pns)``) used
        to pre-seed the search dialog's own search text.
    :returns: The selected part id or :data:`None` when cancelled.
    """
    from PySide6.QtWidgets import QDialog
    from ...ui.dialogs import part_search as _part_search

    page = getattr(mainframe.editor_db.editor, page_name)
    part_id = page.GetSelection()

    if part_id is None:
        dlg = _part_search.SearchDialog(
            mainframe, type(page), table, title, initial_params=initial_params)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            part_id = dlg.GetValue()

        dlg.deleteLater()

    return part_id


@_check_types.do
def trace_circuit(obj3d: "_base_3d.Base3D", db_obj=None):
    """Highlight every project object on the circuit the object belongs to."""
    if db_obj is None:
        db_obj = obj3d.db_obj

    try:
        circuit = db_obj.circuit
    except (AttributeError, KeyError, TypeError):
        circuit = None

    if circuit is None:
        return

    material = _materials.Glowing(
        _color.Color(*_colors_config.add_object.wire_highlight))

    for attr in ('wires', 'wire_service_loops', 'splices', 'terminals'):
        try:
            members = getattr(circuit, attr)
        except (AttributeError, KeyError, TypeError):
            continue

        for member in members:
            obj = member.get_object()
            if obj is not None:
                obj.identify(material)

    obj3d.editor3d.Refresh()
