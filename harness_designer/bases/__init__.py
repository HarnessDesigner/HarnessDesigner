
from .get_angle import GetAngleBase as _GetAngleBase
from .set_angle import SetAngleBase as _SetAngleBase
from .context import ContextBase as _ContextBase


GetAngleBase = _GetAngleBase
SetAngleBase = _SetAngleBase
ContextBase = _ContextBase

del _GetAngleBase
del _SetAngleBase
del _ContextBase
