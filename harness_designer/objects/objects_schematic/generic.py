# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

# from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_schematic as _base_schematic
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import generic as _generic


class Generic(_base_schematic.BaseSchematic):
    """Represent a generic in :mod:`harness_designer.objects.objects_schematic.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_generic.Generic" = None

    @_check_types.do
    def __init__(self, parent: "_generic.Generic", ):
        """Initialise the :class:`Generic` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_generic.Generic`
        """

        super().__init__(parent, None, None, None,
                         None, None, None)

    def render(self, shaders):
        pass
