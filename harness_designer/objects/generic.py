# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_3d import generic as _generic3d
from .objects_schematic import generic as _generic_schematic
from .objects_pegboard import generic as _generic_pegboard
from .. import check_types as _check_types

if TYPE_CHECKING:
    from .. import ui as _ui


class Generic(_ObjectBase):
    """Represent a generic in :mod:`harness_designer.objects.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _generic_schematic.Generic
    obj3d: _generic3d.Generic
    objpegboard: _generic_pegboard.Generic

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`Generic` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__(mainframe, None)

        self.objschematic = _generic_schematic.Generic(self)
        self.obj3d = _generic3d.Generic(self)
        self.objpegboard = _generic_pegboard.Generic(self)
