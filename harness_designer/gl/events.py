# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
GL event system — wx → PySide6

wx used wx.NewEventType() + wx.PyEventBinder() + wx.CommandEvent subclasses.

Qt equivalent: plain Python objects for the event *data* (replacing
CommandEvent subclasses), plus Signal objects on the canvas widget.

The EVT_GL_* names are kept as sentinel objects so that any code that
compares against them continues to work, but they are no longer wx
PyEventBinders.  The real signal wiring is done directly on the canvas
classes using the snake_case signal names (gl_left_down, etc.).

The event *data* classes (GLEvent, GLObjectEvent, GLKeyEvent,
GLCaptureLostEvent) are completely wx-free — they are plain Python
objects.  The only behavioural change is that Skip() / StopPropagation()
are now no-ops:  Qt signals don't propagate through a widget hierarchy
the way wx events do, so callers that call evt.skip() are fine, and
callers that relied on StopPropagation() to block parent handlers should
be reviewed (the canvas handlers in mainframe.py already guard on
self._obj_handler is not None instead).
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import objects as _objects
    from ..geometry import point as _point


# ---------------------------------------------------------------------------
# Sentinel objects — replace wx.PyEventBinder.
# These are only kept for backward-compat isinstance / identity checks.
# The real signal plumbing uses string names on QOpenGLWidget subclasses.
# ---------------------------------------------------------------------------

class _GLEventType:
    """Lightweight sentinel replacing wx.PyEventBinder."""
    __slots__ = ('name',)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f'<GLEventType {self.name}>'


EVT_GL_OBJECT_SELECTED = _GLEventType('EVT_GL_OBJECT_SELECTED')
EVT_GL_OBJECT_UNSELECTED = _GLEventType('EVT_GL_OBJECT_UNSELECTED')
EVT_GL_OBJECT_ACTIVATED = _GLEventType('EVT_GL_OBJECT_ACTIVATED')
EVT_GL_OBJECT_RIGHT_CLICK = _GLEventType('EVT_GL_OBJECT_RIGHT_CLICK')
EVT_GL_OBJECT_RIGHT_DCLICK = _GLEventType('EVT_GL_OBJECT_RIGHT_DCLICK')
EVT_GL_OBJECT_MIDDLE_CLICK = _GLEventType('EVT_GL_OBJECT_MIDDLE_CLICK')
EVT_GL_OBJECT_MIDDLE_DCLICK = _GLEventType('EVT_GL_OBJECT_MIDDLE_DCLICK')
EVT_GL_OBJECT_AUX1_CLICK = _GLEventType('EVT_GL_OBJECT_AUX1_CLICK')
EVT_GL_OBJECT_AUX1_DCLICK = _GLEventType('EVT_GL_OBJECT_AUX1_DCLICK')
EVT_GL_OBJECT_AUX2_CLICK = _GLEventType('EVT_GL_OBJECT_AUX2_CLICK')
EVT_GL_OBJECT_AUX2_DCLICK = _GLEventType('EVT_GL_OBJECT_AUX2_DCLICK')
EVT_GL_OBJECT_DRAG = _GLEventType('EVT_GL_OBJECT_DRAG')

EVT_GL_KEY_DOWN = _GLEventType('EVT_GL_KEY_DOWN')
EVT_GL_KEY_UP = _GLEventType('EVT_GL_KEY_UP')

EVT_GL_MOUSE_MOVE = _GLEventType('EVT_GL_MOUSE_MOVE')

EVT_GL_CAPTURE_LOST = _GLEventType('EVT_GL_CAPTURE_LOST')

EVT_GL_LEFT_DOWN = _GLEventType('EVT_GL_LEFT_DOWN')
EVT_GL_LEFT_UP = _GLEventType('EVT_GL_LEFT_UP')
EVT_GL_LEFT_DCLICK = _GLEventType('EVT_GL_LEFT_DCLICK')

EVT_GL_RIGHT_DOWN = _GLEventType('EVT_GL_RIGHT_DOWN')
EVT_GL_RIGHT_UP = _GLEventType('EVT_GL_RIGHT_UP')
EVT_GL_RIGHT_DCLICK = _GLEventType('EVT_GL_RIGHT_DCLICK')

EVT_GL_MIDDLE_DOWN = _GLEventType('EVT_GL_MIDDLE_DOWN')
EVT_GL_MIDDLE_UP = _GLEventType('EVT_GL_MIDDLE_UP')
EVT_GL_MIDDLE_DCLICK = _GLEventType('EVT_GL_MIDDLE_DCLICK')

EVT_GL_AUX1_DOWN = _GLEventType('EVT_GL_AUX1_DOWN')
EVT_GL_AUX1_UP = _GLEventType('EVT_GL_AUX1_UP')
EVT_GL_AUX1_DCLICK = _GLEventType('EVT_GL_AUX1_DCLICK')

EVT_GL_AUX2_DOWN = _GLEventType('EVT_GL_AUX2_DOWN')
EVT_GL_AUX2_UP = _GLEventType('EVT_GL_AUX2_UP')
EVT_GL_AUX2_DCLICK = _GLEventType('EVT_GL_AUX2_DCLICK')

EVT_GL_DRAG = _GLEventType('EVT_GL_DRAG')


# ---------------------------------------------------------------------------
# Mouse-button bitmask constants (previously wx.MOUSE_BTN_*)
# ---------------------------------------------------------------------------

BTN_NONE = 0x00
BTN_LEFT = 0x01
BTN_RIGHT = 0x02
BTN_MIDDLE = 0x04
BTN_AUX1 = 0x08
BTN_AUX2 = 0x10


# ---------------------------------------------------------------------------
# Event data classes — wx.CommandEvent → plain Python
# ---------------------------------------------------------------------------

class _GLEventBase:
    """Common base for all GL event data objects."""

    def __init__(self, type_):
        self._type = type_
        self._skipped = False
        self._id = None
        self._obj = None
        self._stop_prop = False

    def GetEventType(self):
        return self._type

    def Skip(self):
        self._skipped = True

    # StopPropagation was used in the old wx code to prevent parent-window
    # handlers from seeing the event.  Qt signals don't propagate that way,
    # so this is a no-op kept for call-site compatibility.
    def StopPropagation(self):
        self._stop_prop = True

    def ShouldPropagate(self):
        return self._stop_prop

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


class GLEvent(_GLEventBase):
    """Mouse-position event on a GL canvas."""

    def __init__(self, type_):
        super().__init__(type_)
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_buttons: int = BTN_NONE

    # --- button state ---

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

    # --- positions ---

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

    def __init__(self, type_):
        super().__init__(type_)
        self._gl_object = None
        self._mouse_pos = None
        self._world_pos = None
        self._mouse_buttons: int = BTN_NONE

    # --- button state (same as GLEvent) ---

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

    # --- positions ---

    def GetPosition(self) -> "_point.Point":
        return self._mouse_pos

    def SetPosition(self, pos: "_point.Point") -> None:
        self._mouse_pos = pos

    def GetWorldPosition(self) -> "_point.Point":
        return self._world_pos

    def SetWorldPosition(self, pos: "_point.Point") -> None:
        self._world_pos = pos

    # --- GL object ---

    def GetGLObject(self) -> "_objects.ObjectBase":
        return self._gl_object

    def SetGLObject(self, obj: "_objects.ObjectBase") -> None:
        self._gl_object = obj


class GLKeyEvent(_GLEventBase):
    """Keyboard event on a GL canvas."""

    def __init__(self, type_):
        super().__init__(type_)
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
        self._key_code: int = 0          # Qt.Key value
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
