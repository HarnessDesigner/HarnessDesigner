# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin
from .... import check_types as _check_types


if TYPE_CHECKING:
    from ....ui.prop_ctrls import events as _prop_events
    from PySide6 import QtWidgets


class VisiblePegboardMixin(BaseMixin):
    """Represent a visible pegboard mixin in :mod:`harness_designer.database.project_db.mixins.visible_pegboard`.

    Mirrors :class:`~harness_designer.database.project_db.mixins.visible3d.
    Visible3DMixin` exactly -- every object viewable in the peg-board
    editor gets a ``visible_pegboard`` column controlling whether it
    renders there (e.g. a wire's own bare sections vs. the sections
    covered by its bundle's strand).
    """

    @property
    @_check_types.do
    def is_visible_pegboard(self) -> bool:
        """Return the is visible pegboard.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        _rows = self._table.select('is_visible_pegboard', id=self._db_id)
        return bool(_rows[0][0]) if _rows else None

    @is_visible_pegboard.setter
    @_check_types.do
    def is_visible_pegboard(self, value: bool) -> None:
        """Set the is visible pegboard.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible_pegboard=int(value))
        self._populate('is_visible_pegboard')


class VisiblePegboardControl(_prop_ctrls.BoolProperty):
    """Represent a visible pegboard control in :mod:`harness_designer.database.project_db.mixins.visible_pegboard`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`VisiblePegboardControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: VisiblePegboardMixin | None = None

        super().__init__(parent, 'Is Visible Pegboard')

        self.propertyChanged.connect(self._on_visible_pegboard)

    @_check_types.do
    def _on_visible_pegboard(self, evt: "_prop_events.PropertyEvent") -> None:
        """Handle the visible pegboard event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.is_visible_pegboard = value

    @_check_types.do
    def set_obj(self, db_obj: VisiblePegboardMixin | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`VisiblePegboardMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.is_visible_pegboard)
            self.setEnabled(True)
