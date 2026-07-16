# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ui as _ui
    from .objects3d import base3d as _base3d
    from .objects2d import base2d as _base2d
    from .objectspeg import basepeg as _basepeg
    from ..database import project_db as _project_db


class ObjectBase:
    """Represent an object base in :mod:`harness_designer.objects.object_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: "_base2d.Base2D" = None
    obj3d: "_base3d.Base3D" = None
    objpeg: "_basepeg.BasePeg" = None
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

    def identify(self, material: list[float] | None):
        """Execute the identify operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param material: Value for ``color``.
        :type material: list[float] | None
        """
        if self.obj2d is not None:
            self.obj2d.identify(material)

        if self.obj3d is not None:
            self.obj3d.identify(material)

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

        self.db_obj.delete()

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

        if self.objpeg is not None:
            self.objpeg.set_selected(flag)

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

        if self.objpeg is not None and self.objpeg.is_selected != value:
            self.objpeg.set_selected(value)

    @property
    def is_in_3dview(self) -> bool:
        return self in self.mainframe.editor3d.camera.objects_in_view

    @property
    def is_in_2dview(self) -> bool:
        return self in self.mainframe.editor2d.editor.camera.objects_in_view

    @property
    def is_in_pegboardview(self) -> bool:
        return self in self.mainframe.editor_pegboard.editor.camera.objects_in_view

    @property
    def is_boot(self) -> bool:
        from . import boot as _boot

        return isinstance(self, _boot.Boot)

    @property
    def is_bundle(self) -> bool:
        from . import bundle as _bundle

        return isinstance(self, _bundle.Bundle)

    @property
    def is_bundle_layout(self) -> bool:
        from . import bundle_layout as _bundle_layout

        return isinstance(self, _bundle_layout.BundleLayout)

    @property
    def is_cavity(self) -> bool:
        from . import cavity as _cavity

        return isinstance(self, _cavity.Cavity)

    @property
    def is_circuit(self) -> bool:
        from . import circuit as _circuit

        return isinstance(self, _circuit.Circuit)

    @property
    def is_cover(self) -> bool:
        from . import cover as _cover

        return isinstance(self, _cover.Cover)

    @property
    def is_cpa_lock(self) -> bool:
        from . import cpa_lock as _cpa_lock

        return isinstance(self, _cpa_lock.CPALock)

    @property
    def is_housing(self) -> bool:
        from . import housing as _housing

        return isinstance(self, _housing.Housing)

    @property
    def is_note(self) -> bool:
        from . import note as _note

        return isinstance(self, _note.Note)

    @property
    def is_project(self) -> bool:
        from . import project as _project

        return isinstance(self, _project.Project)

    @property
    def is_seal(self) -> bool:
        from . import seal as _seal

        return isinstance(self, _seal.Seal)

    @property
    def is_splice(self) -> bool:
        from . import splice as _splice

        return isinstance(self, _splice.Splice)

    @property
    def is_terminal(self) -> bool:
        from . import terminal as _terminal

        return isinstance(self, _terminal.Terminal)

    @property
    def is_tpa_lock(self) -> bool:
        from . import tpa_lock as _tpa_lock

        return isinstance(self, _tpa_lock.TPALock)

    @property
    def is_transition(self) -> bool:
        from . import transition as _transition

        return isinstance(self, _transition.Transition)

    @property
    def is_wire(self) -> bool:
        from . import wire as _wire

        return isinstance(self, _wire.Wire)

    @property
    def is_wire_layout(self) -> bool:
        from . import wire_layout as _wire_layout

        return isinstance(self, _wire_layout.WireLayout)

    @property
    def is_wire_marker(self) -> bool:
        from . import wire_marker as _wire_marker

        return isinstance(self, _wire_marker.WireMarker)

    @property
    def is_wire_service_loop(self) -> bool:
        from . import wire_service_loop as _wire_service_loop

        return isinstance(self, _wire_service_loop.WireServiceLoop)


