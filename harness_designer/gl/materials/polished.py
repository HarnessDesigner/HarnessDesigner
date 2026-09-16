# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class PolishedMaterial(_material.GLMaterial):
    """Polished/mirror-finish metal.

    The dimmest fill and the tightest, brightest, most strongly
    color-tinted highlight of any material here -- most of what's seen
    on a polished surface is the reflected highlight itself, not the
    flat underlying color, matching how a real mirror-like finish
    looks.
    """
    _ambient_weight = 0.15
    _diffuse_weight = 0.30
    _specular_weight = 0.65
    _metallic = 1.0
    _shine = 128.0

    _cl_roughness = 0.05
    _cl_reflectivity = 0.75
    _cl_ior = 2.5
