# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from ..canvas_base import mouse_handler_base as _mouse_handler_base


class MouseHandler(_mouse_handler_base.MouseHandlerBase):

    @staticmethod
    def _get_view_object(obj):
        return obj.objpegboard
