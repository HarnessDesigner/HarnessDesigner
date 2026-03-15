
from . import canvas as _canvas
from . import mouse_handler as _mouse_handler


Canvas2D = _canvas.Canvas2D
MouseHandler2D = _mouse_handler.MouseHandler2D
GLEvent2D = _mouse_handler.GLEvent2D

EVT_GL2D_OBJECT_SELECTED = _mouse_handler.EVT_GL2D_OBJECT_SELECTED
EVT_GL2D_OBJECT_UNSELECTED = _mouse_handler.EVT_GL2D_OBJECT_UNSELECTED
EVT_GL2D_OBJECT_ACTIVATED = _mouse_handler.EVT_GL2D_OBJECT_ACTIVATED
EVT_GL2D_OBJECT_RIGHT_CLICK = _mouse_handler.EVT_GL2D_OBJECT_RIGHT_CLICK
EVT_GL2D_OBJECT_DRAG = _mouse_handler.EVT_GL2D_OBJECT_DRAG

del _canvas
del _mouse_handler
