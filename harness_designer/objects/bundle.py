# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import bundle as _bundle_2d
from .objects3d import bundle as _bundle_3d
from .objectspeg import bundle as _bundle_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle as _pjt_bundle


class Bundle(_ObjectBase):
    """Represent a bundle in :mod:`harness_designer.objects.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _bundle_2d.Bundle = None
    obj3d: _bundle_3d.Bundle = None
    objpeg: _bundle_peg.Bundle = None
    db_obj: "_pjt_bundle.PJTBundle" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle.PJTBundle", project_load=False):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _bundle_2d.Bundle(self, db_obj)
        self.obj3d = _bundle_3d.Bundle(self, db_obj)
        self.objpeg = _bundle_peg.Bundle(self, db_obj)
        self.mainframe.add_object(self)

    def delete(self):
        super().delete()
        self.mainframe.project.delete_bundle(self.db_obj.db_id)
        self.db_obj.delete()

    # TODO: We need to move things like wires so they are held here.
    #       anything that is held in any of the obj* class instances should
    #       only hold objects that areof the same instance type

    def _delete(self):
        """Override delete to restore wire visibility."""
        # Restore visibility of all wires before deleting
        for ref in self._wires[:]:
            wire = ref()
            if wire is not None:
                wire.is_visible = True

        self._wires.clear()
        super()._delete()
