# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui
    from .objects3d import base3d as _base3d
    from .objects2d import base2d as _base2d
    from ..database import project_db as _project_db


class ObjectBase:
    """Represent an object base in :mod:`harness_designer.objects.object_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: "_base2d.Base2D" = None
    obj3d: "_base3d.Base3D" = None
    db_obj: "_project_db.PJTEntryBase" = None

    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_project_db.PJTEntryBase"):
        """Initialise the :class:`ObjectBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        """
        self.mainframe: "_ui.MainFrame" = mainframe

        self._deleted = False
        self._is_selected = False
        self._treeitem = None
        self.db_obj = db_obj

    def identify(self, color: list[float] | None):
        """Execute the identify operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param color: Value for ``color``.
        :type color: list[float] | None
        """
        if self.obj2d is not None:
            self.obj2d.identify(color)

        if self.obj3d is not None:
            self.obj3d.identify(color)

    def set_treeitem(self, treeitem):
        """Set the treeitem.

        UNKNOWN details are inferred from the callable name and signature.

        :param treeitem: Value for ``treeitem``.
        :type treeitem: UNKNOWN
        """
        self._treeitem = treeitem

    def get_treeitem(self):
        """Return the treeitem.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._treeitem

    def delete(self):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._deleted:
            return

        self._deleted = True
        if self.obj2d is not None:
            self.obj2d.delete()

        if self.obj3d is not None:
            self.obj3d.delete()

    def close(self):
        """Execute the close operation.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def set_selected(self, flag):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: UNKNOWN
        """
        self._is_selected = flag

        if self.obj2d is not None:
            self.obj2d.set_selected(flag)
        if self.obj3d is not None:
            self.obj3d.set_selected(flag)

        if flag:
            self.mainframe._set_selected(self)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        """Set the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_selected = value

        if self.obj2d is not None and self.obj2d.is_selected != value:
            self.obj2d.set_selected(value)

        if self.obj3d is not None and self.obj3d.is_selected != value:
            self.obj3d.set_selected(value)

    @property
    def propgrid(self):
        """Return the propgrid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self.obj3d is not None:
            if self.obj3d.db_obj is not None:
                return self.obj3d.db_obj.propgrid

        if self.obj2d is not None:
            if self.obj2d.db_obj is not None:
                return self.obj2d.db_obj.propgrid

        return []
