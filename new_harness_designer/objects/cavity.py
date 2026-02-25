from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import cavity as _cavity_2d
from .objects3d import cavity as _cavity_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cavity as _pjt_cavity
    from . import housing as _housing
    from . import terminal as _terminal
    from . import seal as _seal


class Cavity(_ObjectBase):
    obj2d: _cavity_2d.Cavity = None
    obj3d: _cavity_3d.Cavity = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_cavity.PJTCavity", housing: "_housing.Housing"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.housing = housing
        self.obj2d = _cavity_2d.Cavity(self, db_obj)
        self.obj3d = _cavity_3d.Cavity(self, db_obj)

        self.seal = None
        self.terminal = None

    def add_terminal(self, terminal: "_terminal.Terminal"):
        self.terminal = terminal

    def add_seal(self, seal: "_seal.Seal"):
        self.seal = seal

