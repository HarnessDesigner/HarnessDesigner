from . import part as _part
from . import angle as _angle
from . import position as _position
from . import dimension as _dimension
from . import visible as _visible
from . import weight as _weight
from . import scale as _scale

PartMixin = _part.PartMixin
Angle3DMixin = _angle.Angle3DMixin
Angle2DMixin = _angle.Angle2DMixin
Position2DMixin = _position.Position2DMixin
Position3DMixin = _position.Position3DMixin
DimensionMixin = _dimension.DimensionMixin
Visible3DMixin = _visible.Visible3DMixin
Visible2DMixin = _visible.Visible2DMixin
WeightMixin = _weight.WeightMixin
Scale3DMixin = _scale.Scale3DMixin

del _part
del _angle
del _position
del _dimension
del _visible
del _weight
del _scale
