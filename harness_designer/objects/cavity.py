# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_schematic import cavity as _cavity_schematic
from .objects3d import cavity as _cavity_3d
from .objectspeg import cavity as _cavity_peg
from .. import check_types as _check_types


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
    objschematic: _cavity_schematic.Cavity = None
    obj3d: _cavity_3d.Cavity = None
    objpeg: _cavity_peg.Cavity = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    @_check_types.do
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

        self.objschematic = _cavity_schematic.Cavity(self, db_obj)
        self.obj3d = _cavity_3d.Cavity(self, db_obj)
        self.objpeg = _cavity_peg.Cavity(self, db_obj)

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def terminal(self):
        terminal = self.db_obj.terminal
        if terminal is None:
            return None

        return terminal.get_object()

    @property
    @_check_types.do
    def housing(self):
        """This cavity's owning ``Housing`` wrapper -- lets a terminal
        reach its housing via ``db_obj.cavity.get_object().housing``
        (see ``objects_schematic/terminal.py``'s ``Terminal``), and a cavity
        reach it directly via ``self.parent.housing`` (see
        ``objects_schematic/cavity.py``'s ``Cavity``).

        Resolved on demand from ``PJTCavity.housing`` (a real
        ``housing_id`` column, via ``HousingMixin``), not cached -- by
        the time anything calls this (a name/terminal_id callback
        firing, never at construction time), this cavity's housing is
        guaranteed to already exist and be registered (see
        ``objects/housing.py``'s ``Housing.__init__``/
        ``_construct_cavities``).
        """
        housing_db = self.db_obj.housing
        if housing_db is None:
            return None

        return housing_db.get_object()

    @property
    @_check_types.do
    def seal(self):
        seal = self.db_obj.seal
        if seal is None:
            return None

        return seal.get_object()

    @_check_types.do
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
