
from . import generic as _generic
from . import material as _material
from . import metallic as _metallic
from . import plastic as _plastic
from . import polished as _polished
from . import rubber as _rubber


Generic = _generic.GenericMaterial
GLMaterial = _material.GLMaterial
Metallic = _metallic.MetallicMaterial
Plastic = _plastic.PlasticMaterial
Polished = _polished.PolishedMaterial
Rubber = _rubber.RubberMaterial


del _generic
del _material
del _plastic
del _metallic
del _polished
del _rubber
