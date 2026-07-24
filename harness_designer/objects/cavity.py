# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cavity as _cavity_2d
from .objects3d import cavity as _cavity_3d
from .objectspeg import cavity as _cavity_peg


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cavity as _pjt_cavity
    from . import housing as _housing
    from . import terminal as _terminal
    from . import seal as _seal


class Cavity(_ObjectBase):
    """Represent a cavity in :mod:`harness_designer.objects.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _cavity_2d.Cavity = None
    obj3d: _cavity_3d.Cavity = None
    objpeg: _cavity_peg.Cavity = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cavity.PJTCavity", project_load=False):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _cavity_2d.Cavity(self, db_obj)
        self.obj3d = _cavity_3d.Cavity(self, db_obj)
        self.objpeg = _cavity_peg.Cavity(self, db_obj)

        self.mainframe.add_object(self)

    @property
    def terminal(self):
        terminal = self.db_obj.terminal
        if terminal is None:
            return None

        return terminal.get_object()

    @property
    def seal(self):
        seal = self.db_obj.seal
        if seal is None:
            return None

        return seal.get_object()

    def delete(self):
        super().delete()

        terminal = self.terminal
        seal = self.seal

        if terminal is not None:
            terminal.delete()

        if seal is not None:
            seal.delete()

        self.mainframe.project.delete_cavity(self.db_obj.db_id)
        self.db_obj.delete()
