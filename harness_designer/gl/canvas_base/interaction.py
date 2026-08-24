# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Mouse-interaction kinds passed to ``BaseVar.handle_interaction``.

A small, dispatch-specific enum -- deliberately not the existing
``gl.events.EVT_GL_*`` string constants, which also cover camera and
object-selection events that have nothing to do with an armed add/drag/
rotation handler. Every kind here corresponds to something
``MouseHandlerBase`` already computes on the relevant ``on_*`` call before
deciding whether to route it to ``CanvasBase.active_handler_obj``.
"""

import enum


class MouseInteraction(enum.Enum):
    MOVE = 'move'
    LEFT_DOWN = 'left_down'
    LEFT_UP = 'left_up'
    RIGHT_DOWN = 'right_down'
    RIGHT_UP = 'right_up'
    MIDDLE_DOWN = 'middle_down'
    MIDDLE_UP = 'middle_up'
    CANCEL = 'cancel'
