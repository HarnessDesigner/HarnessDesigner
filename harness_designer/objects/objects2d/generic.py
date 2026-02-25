from typing import TYPE_CHECKING

import numpy as np

# from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base2d as _base2d
from ...gl import vbo as _vbo
from ...gl import materials as _materials


if TYPE_CHECKING:
    from .. import generic as _generic


class Generic(_base2d.Base2D):
    _parent: "_generic.Generic" = None

    def __init__(self, parent: "_generic.Generic", ):

        _base2d.Base2D.__init__(self, parent, None)
