# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union


# from ...widgets.context_menus import RotateMenu, MirrorMenu
from . import base_schematic as _base_schematic
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl import shaders as _shaders
    from .. import generic as _generic
    from ...gl.canvas_3d import focal_target as _focal_target


class Generic(_base_schematic.BaseSchematic):
    """Represent a generic in :mod:`harness_designer.objects.objects_schematic.generic`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_generic.Generic" = None

    @_check_types.do
    def __init__(self, parent: _Union["_generic.Generic", "_focal_target.FocalTarget"], ):
        """Initialise the :class:`Generic` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_generic.Generic`
        """

        super().__init__(parent, None, None, None,
                         None, None, None)

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        pass
