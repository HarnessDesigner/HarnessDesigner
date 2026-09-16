# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ... import color as _color
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ..shaders import program as _shader_program


class GLMaterial:
    """Base material for Phong shading.

    A material "type" (metal, polished metal, plastic, rubber, ...) is
    nothing more than a handful of scalar weights applied directly to
    the caller's own color -- never a separate, hand-picked ambient/
    diffuse/specular RGB triple. ``ambient``/``diffuse`` are always the
    true input color times a plain scalar (``_ambient_weight``/
    ``_diffuse_weight``), so every channel is scaled by the exact same
    number and the fill can never shift hue on its own -- only its
    brightness changes between material types. The one place hue can
    shift at all is the specular highlight, which for a metal
    (``_metallic`` > 0) is deliberately tinted toward the material's
    own color -- that tint IS a metal's visual signature, and stays
    confined to the small hot-spot the shininess exponent produces, not
    smeared across the whole surface. A dielectric (plastic, rubber,
    ..., ``_metallic`` == 0.0) keeps a neutral white highlight instead,
    matching how a real non-metal actually reflects light.

    This replaces an earlier design where every material subclass
    invented its own ambient/diffuse/specular RGB formula from the
    input color -- several of those formulas mixed in fixed, colorless
    constants (a flat grey specular, a flat ambient floor) alongside
    the true color, and the renderer sums ambient+diffuse+specular in
    the shader with a hard per-channel clamp on overflow. Both of those
    combine to visibly shift the color that actually reaches the
    screen away from the color that was asked for -- a fixed grey
    added to an unevenly-saturated color desaturates it, and clamping
    a per-channel sum that exceeds 1.0 clips whichever channel got
    there first, changing the ratio between channels (i.e. the hue).
    Deriving ambient/diffuse as a single proportional scale of the true
    color, and keeping the weights low enough that the ordinary (non
    hot-spot) case never approaches that overflow, avoids the first
    problem structurally; the fragment shader's own overflow handling
    (``gl/shaders/faces/fragment.frag``) was changed to rescale all
    three channels together instead of clamping each one independently,
    which fixes the second problem for every material at once,
    including this one's rare hot-spot overflows.

    These same scalar weights (``_cl_roughness``/``_cl_reflectivity``/
    ``_cl_ior``, plus ``_ambient_weight``/``_diffuse_weight``/
    ``_specular_weight``/``_metallic``/``_shine`` themselves) also drive
    the offline ray-traced renderer (see ``ray_tracing/kernel.cl``'s
    ``Material`` struct) -- that renderer already treated ambient/
    diffuse/specular as plain scalar multipliers on the true color, so
    this class now matches it instead of the rasterizer inventing its
    own separate scheme.
    """

    # Fraction of the true color that shows in the unlit/ambient fill.
    _ambient_weight = 0.35

    # Fraction of the true color that shows in the direct-light fill.
    _diffuse_weight = 0.55

    # Strength of the specular highlight (0.0 disables it entirely).
    _specular_weight = 0.25

    # 0.0 = dielectric (neutral/white highlight, e.g. plastic, rubber).
    # 1.0 = metal (highlight tinted by the material's own color).
    _metallic = 0.0

    # Highlight tightness, 0.0-128.0 -- low = broad, soft highlight
    # (rubber), high = small, hot highlight (polished metal).
    _shine = 40.0

    # Light emitting like LEDs -- only ``GlowingMaterial`` sets this to
    # something other than black.
    _emissive = (0.0, 0.0, 0.0, 0.0)

    # Same scalar weights, consumed by the offline ray tracer (see
    # ``cl_array``/``ray_tracing/kernel.cl``'s ``Material`` struct) --
    # not used by the GL rasterizer at all.
    _cl_roughness = 0.5
    _cl_reflectivity = 0.1
    _cl_ior = 1.45

    @_check_types.do
    def __init__(self, color: _color.Color):
        """Initialise the :class:`GLMaterial` instance.

        :param color: The material's true color -- every shading term
            this class computes is a direct, proportional function of
            it (see the class docstring).
        :type color: :class:`_color.Color`
        """
        self._color = color

        r, g, b, a = color.rgba_scalar
        self._is_opaque = a == 1.0

        self.ambient = np.array(
            (r * self._ambient_weight, g * self._ambient_weight,
             b * self._ambient_weight, a), dtype=np.float32)

        self.diffuse = np.array(
            (r * self._diffuse_weight, g * self._diffuse_weight,
             b * self._diffuse_weight, a), dtype=np.float32)

        # Lerp the highlight color between neutral white (dielectric)
        # and the true color (metal), per-channel, driven by _metallic.
        tint_r = 1.0 - self._metallic * (1.0 - r)
        tint_g = 1.0 - self._metallic * (1.0 - g)
        tint_b = 1.0 - self._metallic * (1.0 - b)

        self.specular = np.array(
            (tint_r * self._specular_weight, tint_g * self._specular_weight,
             tint_b * self._specular_weight, a), dtype=np.float32)

        self.shininess = self._shine
        self.emissive = np.array(self._emissive, dtype=np.float32)

    @property
    @_check_types.do
    def cl_array(self):
        """Return this material packed for the offline ray tracer.

        Layout matches ``ray_tracing/kernel.cl``'s ``Material`` struct
        exactly: ``r, g, b, ambient, diffuse, specular, shininess,
        metallic, roughness, reflectivity, transparency, ior``.

        :returns: The 12-float material record the ray tracer expects.
        :rtype: numpy.ndarray
        """
        r, g, b, a = self._color.rgba_scalar

        return np.array(
            [r, g, b, self._ambient_weight, self._diffuse_weight,
             self._specular_weight, self._shine, self._metallic,
             self._cl_roughness, self._cl_reflectivity, a,
             self._cl_ior], dtype=np.float32)

    @property
    @_check_types.do
    def color_scalar(self):
        """Return the material's true color, unmodified by lighting.

        :returns: RGBA scalar tuple in 0.0-1.0.
        :rtype: tuple[float, float, float, float]
        """
        return self._color.rgba_scalar

    @property
    @_check_types.do
    def is_opaque(self):
        """Report whether this material's color is fully opaque.

        :returns: ``True`` when alpha is 1.0.
        :rtype: bool
        """
        return self._is_opaque

    @_check_types.do
    def set(self, program: _Union["_shader_program.FacesProgram", "_shader_program.EdgesProgram"]):
        """Push this material's uniforms onto the given (already-bound) program.

        :param program: The faces or edges program currently bound via
            ``with program:``.
        """

        program.material_ambient = self.ambient
        program.material_diffuse = self.diffuse
        program.material_specular = self.specular
        program.material_shininess = self.shininess
        program.material_emissive = self.emissive

        if not hasattr(type(program), "emissive_rim_power"):
            return

        if (
            self.emissive[0] != 0.0 or
            self.emissive[1] != 0.0 or
            self.emissive[2] != 0.0
        ):
            rim = sum(float(str(v)) for v in self.emissive[:-1].tolist()) * 2
            program.emissive_rim_power = rim
            program.emissive_rim_intensity = rim
        else:
            program.emissive_rim_power = 0.0
            program.emissive_rim_intensity = 0.0
