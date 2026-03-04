from . import angle as _angle
from . import quaternion as _quaternion


Angle = _angle.Angle
Quaternion = _quaternion.Quaternion

del _angle
del _quaternion
