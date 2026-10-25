# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import generic as _generic
from . import material as _material
from . import metallic as _metallic
from . import plastic as _plastic
from . import polished as _polished
from . import rubber as _rubber
from . import glowing as _glowing
from . import circuit as _circuit


Generic = _generic.GenericMaterial
GLMaterial = _material.GLMaterial
Metallic = _metallic.MetallicMaterial
Plastic = _plastic.PlasticMaterial
Polished = _polished.PolishedMaterial
Rubber = _rubber.RubberMaterial
Glowing = _glowing.GlowingMaterial
Circuit = _circuit.CircuitMaterial

del _generic
del _material
del _plastic
del _metallic
del _polished
del _rubber
del _glowing
del _circuit
