# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class GenericMaterial(_material.GLMaterial):
    """Default catch-all material.

    Moderate fill brightness and a modest neutral highlight -- used
    wherever no specific real-world material applies (labels, schematic
    fills, generic previews). Uses ``GLMaterial``'s own defaults
    explicitly so this class stays self-documenting.
    """
    _ambient_weight = 0.35
    _diffuse_weight = 0.55
    _specular_weight = 0.25
    _metallic = 0.0
    _shine = 40.0
