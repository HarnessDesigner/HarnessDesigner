# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
GL event system — wx → PySide6

The EVT_GL_* constants are plain strings that match the Qt Signal names
declared on the canvas classes.  Passing one to canvas.connect() or
editor.connect() directly selects the right signal:

    editor3d.connect(EVT_GL_OBJECT_SELECTED, self._on_obj_selected_3d)

The event data classes (GLEvent, GLObjectEvent, GLKeyEvent,
GLCaptureLostEvent) are plain Python objects that carry all contextual
information (positions, button state, the GL object that was hit, etc.)
to the handler.  They are emitted through the matching Qt Signal and
received directly by the connected handler — no conversion step needed.
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import objects as _objects
    from ..geometry import point as _point


# ---------------------------------------------------------------------------
# EVT_GL_* constants — plain strings matching the Signal names on the canvas.
# Pass directly to editor.connect() / canvas.connect().
# ---------------------------------------------------------------------------

EVT_GL_OBJECT_SELECTED      = 'gl_object_selected'
EVT_GL_OBJECT_UNSELECTED    = 'gl_object_unselected'
EVT_GL_OBJECT_ACTIVATED     = 'gl_object_activated'
EVT_GL_OBJECT_RIGHT_CLICK   = 'gl_object_right_click'
EVT_GL_OBJECT_RIGHT_DCLICK  = 'gl_object_right_dclick'
EVT_GL_OBJECT_MIDDLE_CLICK  = 'gl_object_middle_click'
EVT_GL_OBJECT_MIDDLE_DCLICK = 'gl_object_middle_dclick'
EVT_GL_OBJECT_AUX1_CLICK    = 'gl_object_aux1_click'
EVT_GL_OBJECT_AUX1_DCLICK   = 'gl_object_aux1_dclick'
EVT_GL_OBJECT_AUX2_CLICK    = 'gl_object_aux2_click'
EVT_GL_OBJECT_AUX2_DCLICK   = 'gl_object_aux2_dclick'
EVT_GL_OBJECT_DRAG          = 'gl_object_drag'

EVT_GL_KEY_DOWN    = 'gl_key_down'
EVT_GL_KEY_UP      = 'gl_key_up'

EVT_GL_MOUSE_MOVE   = 'gl_mouse_move'

EVT_GL_CAPTURE_LOST = 'gl_capture_lost'

EVT_GL_LEFT_DOWN    = 'gl_left_down'
EVT_GL_LEFT_UP      = 'gl_left_up'
EVT_GL_LEFT_DCLICK  = 'gl_left_dclick'

EVT_GL_RIGHT_DOWN   = 'gl_right_down'
EVT_GL_RIGHT_UP     = 'gl_right_up'
EVT_GL_RIGHT_DCLICK = 'gl_right_dclick'

EVT_GL_MIDDLE_DOWN   = 'gl_middle_down'
EVT_GL_MIDDLE_UP     = 'gl_middle_up'
EVT_GL_MIDDLE_DCLICK = 'gl_middle_dclick'

EVT_GL_AUX1_DOWN   = 'gl_aux1_down'
EVT_GL_AUX1_UP     = 'gl_aux1_up'
EVT_GL_AUX1_DCLICK = 'gl_aux1_dclick'

EVT_GL_AUX2_DOWN   = 'gl_aux2_down'
EVT_GL_AUX2_UP     = 'gl_aux2_up'
EVT_GL_AUX2_DCLICK = 'gl_aux2_dclick'

EVT_GL_DRAG = 'gl_drag'


# ---------------------------------------------------------------------------
# Mouse-button bitmask constants (previously wx.MOUSE_BTN_*)
# ---------------------------------------------------------------------------

BTN_NONE   = 0x00
BTN_LEFT   = 0x01
BTN_RIGHT  = 0x02
BTN_MIDDLE = 0x04
BTN_AUX1   = 0x08
BTN_AUX2   = 0x10


# ---------------------------------------------------------------------------
# Event data classes — wx.CommandEvent → plain Python
# ---------------------------------------------------------------------------

class _GLEventBase:
    """Common base for all GL event data objects."""

    def __init__(self):
        self._skipped = False
        self._id = None
        self._obj = None
        self._stop_prop = False

    def Skip(self):
        self._skipped = True

    def StopPropagation(self):
        self._stop_prop = True

    def ShouldPropagate(self):
        return not self._stop_prop

    def SetId(self, id_):
        self._id = id_

    def GetId(self):
        return self._id

    def SetEventObject(self, obj):
        self._obj = obj

    def GetEventObject(self):
        return self._obj

    @property
    def GetSkipped(self) -> bool:
        return self._skipped


class GLCaptureLostEvent(_GLEventBase):
    """Emitted when the canvas loses mouse capture."""
    pass


class GLEvent(_GLEventBase):
    """Mouse-position event on a GL canvas."""

    def __init__(self):
        super().__init__()
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_buttons: int = BTN_NONE

    def RightIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_RIGHT)

    def LeftIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_LEFT)

    def MiddleIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_MIDDLE)

    def Aux1IsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_AUX1)

    def Aux2IsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_AUX2)

    def SetMouseButtons(self, buttons: int) -> None:
        self._mouse_buttons = buttons

    def GetMouseButtons(self) -> int:
        return self._mouse_buttons

    def GetPosition(self) -> "_point.Point":
        return self._mouse_pos

    def SetPosition(self, pos: "_point.Point") -> None:
        self._mouse_pos = pos

    def GetWorldPosition(self) -> "_point.Point":
        return self._world_pos

    def SetWorldPosition(self, pos: "_point.Point") -> None:
        self._world_pos = pos


class GLObjectEvent(_GLEventBase):
    """Mouse interaction with a specific GL object."""

    def __init__(self):
        super().__init__()
        self._gl_object = None
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_buttons: int = BTN_NONE

    def RightIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_RIGHT)

    def LeftIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_LEFT)

    def MiddleIsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_MIDDLE)

    def Aux1IsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_AUX1)

    def Aux2IsDown(self) -> bool:
        return bool(self._mouse_buttons & BTN_AUX2)

    def SetMouseButtons(self, buttons: int) -> None:
        self._mouse_buttons = buttons

    def GetMouseButtons(self) -> int:
        return self._mouse_buttons

    def GetPosition(self) -> "_point.Point":
        return self._mouse_pos

    def SetPosition(self, pos: "_point.Point") -> None:
        self._mouse_pos = pos

    def GetWorldPosition(self) -> "_point.Point":
        return self._world_pos

    def SetWorldPosition(self, pos: "_point.Point") -> None:
        self._world_pos = pos

    def GetGLObject(self) -> "_objects.ObjectBase":
        return self._gl_object

    def SetGLObject(self, obj: "_objects.ObjectBase") -> None:
        self._gl_object = obj


class GLKeyEvent(_GLEventBase):
    """Keyboard event on a GL canvas."""

    def __init__(self):
        super().__init__()
        self._pos = None
        self._world_pos = None
        self._mouse_event: GLObjectEvent | GLEvent | None = None
        self._alt_down = False
        self._cmd_down = False
        self._ctrl_down = False
        self._modifiers = 0
        self._meta_down = False
        self._raw_ctrl_down = False
        self._shift_down = False
        self._key_code: int = 0
        self._raw_key_code: int = 0
        self._raw_key_flags: int = 0
        self._unicode_key: int = 0

    def GetMouseEvent(self) -> "GLObjectEvent | GLEvent | None":
        return self._mouse_event

    def SetMouseEvent(self, evt: "GLObjectEvent | GLEvent | None") -> None:
        self._mouse_event = evt

    def AltDown(self) -> bool:
        return self._alt_down

    def SetAltDown(self, value: bool) -> None:
        self._alt_down = value

    def CmdDown(self) -> bool:
        return self._cmd_down

    def SetCmdDown(self, value: bool) -> None:
        self._cmd_down = value

    def ControlDown(self) -> bool:
        return self._ctrl_down

    def SetControlDown(self, value: bool) -> None:
        self._ctrl_down = value

    def GetModifiers(self) -> int:
        return self._modifiers

    def SetModifiers(self, modifiers: int) -> None:
        self._modifiers = modifiers

    def MetaDown(self) -> bool:
        return self._meta_down

    def SetMetaDown(self, value: bool) -> None:
        self._meta_down = value

    def RawControlDown(self) -> bool:
        return self._raw_ctrl_down

    def SetRawControlDown(self, value: bool) -> None:
        self._raw_ctrl_down = value

    def ShiftDown(self) -> bool:
        return self._shift_down

    def SetShiftDown(self, value: bool) -> None:
        self._shift_down = value

    def GetKeyCode(self) -> int:
        return self._key_code

    def SetKeyCode(self, code: int) -> None:
        self._key_code = code

    def GetRawKeyCode(self) -> int:
        return self._raw_key_code

    def SetRawKeyCode(self, code: int) -> None:
        self._raw_key_code = code

    def GetRawKeyFlags(self) -> int:
        return self._raw_key_flags

    def SetRawKeyFlags(self, flags: int) -> None:
        self._raw_key_flags = flags

    def GetUnicodeKey(self) -> int:
        return self._unicode_key

    def SetUnicodeKey(self, key: int) -> None:
        self._unicode_key = key

    def GetPosition(self) -> "_point.Point":
        return self._pos

    def SetPosition(self, pos: "_point.Point") -> None:
        self._pos = pos

    def GetWorldPosition(self) -> "_point.Point":
        return self._world_pos

    def SetWorldPosition(self, pos: "_point.Point") -> None:
        self._world_pos = pos
