# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class MetallicMaterial(_material.GLMaterial):
    """Brushed/raw metal.

    A dimmer fill than a dielectric (real metal has very little diffuse
    reflection -- its character comes from the reflective highlight,
    not the flat fill) topped with a broad highlight tinted by the
    material's own color, per ``GLMaterial``'s ``_metallic`` blend.
    """
    _ambient_weight = 0.25
    _diffuse_weight = 0.45
    _specular_weight = 0.45
    _metallic = 1.0
    _shine = 50.0

    _cl_roughness = 0.4
    _cl_reflectivity = 0.35
    _cl_ior = 2.5
