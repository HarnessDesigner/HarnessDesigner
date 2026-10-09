# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from typing import TYPE_CHECKING

from ..canvas_base import mouse_handler_base as _mouse_handler_base


if TYPE_CHECKING:
    from ... import objects as _objects
    from ...objects.objectsvar import base_var as _base_var


class MouseHandler(_mouse_handler_base.MouseHandlerBase):

    @staticmethod
    def _get_view_object(obj: "_objects.ObjectBase") -> "_base_var.BaseVar":
        return obj.objschematic
