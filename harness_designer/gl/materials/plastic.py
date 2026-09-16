# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class PlasticMaterial(_material.GLMaterial):
    """Injection-molded plastic.

    A bright, fully color-accurate fill (see ``GLMaterial``'s
    docstring) with a moderately tight, neutral-white highlight on top
    -- a real plastic's specular glint isn't tinted by its own color,
    unlike a metal's (see ``MetallicMaterial``/``PolishedMaterial``).
    """
    _ambient_weight = 0.30
    _diffuse_weight = 0.60
    _specular_weight = 0.35
    _metallic = 0.0
    _shine = 70.0

    _cl_roughness = 0.25
    _cl_reflectivity = 0.08
    _cl_ior = 1.5
