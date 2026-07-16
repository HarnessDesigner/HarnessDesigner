# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import generic as _generic3d
from .objects2d import generic as _generic2d
from .objectspeg import generic as _genericpeg

if TYPE_CHECKING:
    from .. import ui as _ui


class Generic(_ObjectBase):
    """Represent a generic in :mod:`harness_designer.objects.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _generic2d.Generic
    obj3d: _generic3d.Generic
    objpeg: _genericpeg.Generic

    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`Generic` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """

        super().__init__(mainframe, None)

        self.obj2d = _generic2d.Generic(self)
        self.obj3d = _generic3d.Generic(self)
        self.objpeg = _genericpeg.Generic(self)
