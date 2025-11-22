# TODO: I do not believe I am going to be uses these base classes anymore.
#       So they are only here as a just in case scenario


from .get_angle import GetAngleBase as _GetAngleBase
from .set_angle import SetAngleBase as _SetAngleBase
from .context import ContextBase as _ContextBase


GetAngleBase = _GetAngleBase
SetAngleBase = _SetAngleBase
ContextBase = _ContextBase

del _GetAngleBase
del _SetAngleBase
del _ContextBase
