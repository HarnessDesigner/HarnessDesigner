
from . import adhesive as _adhesive
from . import color as _color
from . import resource as _resource
from . import description as _description
from . import dimension as _dimension
from . import direction as _direction
from . import family as _family
from . import gender as _gender
from . import manufacturer as _manufacturer
from . import material as _material
from . import name as _name
from . import part_number as _part_number
from . import series as _series
from . import temperature as _temperature
from . import wire_size as _wire_size
from . import protection as _protection
from . import weight as _weight
from . import cavity_lock as _cavity_lock
from . import model3d as _model3d
from . import plating as _plating
from . import compat_housings as _compat_housings
from . import compat_terminals as _compat_terminals
from . import compat_seals as _compat_seals


ColorMixin = _color.ColorMixin
ResourceMixin = _resource.ResourceMixin
DescriptionMixin = _description.DescriptionMixin
DimensionMixin = _dimension.DimensionMixin
DirectionMixin = _direction.DirectionMixin
FamilyMixin = _family.FamilyMixin
GenderMixin = _gender.GenderMixin
ManufacturerMixin = _manufacturer.ManufacturerMixin
MaterialMixin = _material.MaterialMixin
NameMixin = _name.NameMixin
PartNumberMixin = _part_number.PartNumberMixin
SeriesMixin = _series.SeriesMixin
TemperatureMixin = _temperature.TemperatureMixin
WireSizeMixin = _wire_size.WireSizeMixin
AdhesiveMixin = _adhesive.AdhesiveMixin
ProtectionMixin = _protection.ProtectionMixin
WeightMixin = _weight.WeightMixin
CavityLockMixin = _cavity_lock.CavityLockMixin
Model3DMixin = _model3d.Model3DMixin
PlatingMixin = _plating.PlatingMixin
CompatHousingsMixin = _compat_housings.CompatHousingsMixin
CompatTerminalsMixin = _compat_terminals.CompatTerminalsMixin
CompatSealsMixin = _compat_seals.CompatSealsMixin


del _adhesive
del _color
del _description
del _dimension
del _direction
del _family
del _gender
del _resource
del _manufacturer
del _material
del _name
del _part_number
del _series
del _temperature
del _wire_size
del _protection
del _weight
del _cavity_lock
del _model3d
del _plating
del _compat_housings
del _compat_terminals
del _compat_seals
