# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class RubberMaterial(_material.GLMaterial):
    """Rubber.

    Almost entirely a flat, fully color-accurate fill (see
    ``GLMaterial``'s docstring) -- a broad, very low, neutral highlight
    and no metallic tint, matching how matte rubber barely glints at
    all.
    """
    _ambient_weight = 0.35
    _diffuse_weight = 0.62
    _specular_weight = 0.06
    _metallic = 0.0
    _shine = 8.0

    _cl_roughness = 0.9
    _cl_reflectivity = 0.01
    _cl_ior = 1.5
