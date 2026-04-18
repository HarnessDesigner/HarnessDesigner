
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
ColorControl = _color.ColorControl

ResourceMixin = _resource.ResourceMixin
ResourcesControl = _resource.ResourcesControl

DescriptionMixin = _description.DescriptionMixin
DescriptionControl = _description.DescriptionControl

DimensionMixin = _dimension.DimensionMixin
DimensionControl = _dimension.DimensionControl

DirectionMixin = _direction.DirectionMixin
DirectionControl = _direction.DirectionControl

FamilyMixin = _family.FamilyMixin
FamilyControl = _family.FamilyControl

GenderMixin = _gender.GenderMixin
GenderControl = _gender.GenderControl

ManufacturerMixin = _manufacturer.ManufacturerMixin
ManufacturerControl = _manufacturer.ManufacturerControl

MaterialMixin = _material.MaterialMixin
MaterialControl = _material.MaterialControl

NameMixin = _name.NameMixin
NameControl = _name.NameControl

PartNumberMixin = _part_number.PartNumberMixin
PartNumberControl = _part_number.PartNumberControl

SeriesMixin = _series.SeriesMixin
SeriesControl = _series.SeriesControl

TemperatureMixin = _temperature.TemperatureMixin
TemperatureControl = _temperature.TemperatureControl

WireSizeMixin = _wire_size.WireSizeMixin
WireSizeControl = _wire_size.WireSizeControl

AdhesiveMixin = _adhesive.AdhesiveMixin
AdhesiveControl = _adhesive.AdhesiveControl

ProtectionMixin = _protection.ProtectionMixin
ProtectionControl = _protection.ProtectionControl

WeightMixin = _weight.WeightMixin
WeightControl = _weight.WeightControl

CavityLockMixin = _cavity_lock.CavityLockMixin
CavityLockControl = _cavity_lock.CavityLockControl

Model3DMixin = _model3d.Model3DMixin
Model3DControl = _model3d.Model3DControl

PlatingMixin = _plating.PlatingMixin
PlatingControl = _plating.PlatingControl

CompatHousingsMixin = _compat_housings.CompatHousingsMixin
CompatHousingsControl = _compat_housings.CompatHousingsControl

CompatTerminalsMixin = _compat_terminals.CompatTerminalsMixin
CompatTerminalsControl = _compat_terminals.CompatTerminalsControl

CompatSealsMixin = _compat_seals.CompatSealsMixin
CompatSealsControl = _compat_seals.CompatSealsControl


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
