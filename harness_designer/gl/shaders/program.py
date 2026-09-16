import numpy as np
from OpenGL import GL

from . import edges as _edges
from . import faces as _faces
from . import floor as _floor
from . import grid2d as _grid2d
from . import texture as _texture
from . import vertices as _vertices


class Program:

    def __init__(self, program):
        self._program = program
        self._ref_count = 0

    def __enter__(self):
        self._ref_count += 1
        if self._ref_count == 1:
            GL.glUseProgram(self._program)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1
        if self._ref_count == 0:
            GL.glUseProgram(0)


class FacesProgram(Program):

    def __init__(self):
        program = _faces.compile_program()
        super().__init__(program)

        with self:
            self._view_position = GL.glGetUniformLocation(program, 'viewPosition')
            self._projection = GL.glGetUniformLocation(program, 'projection')
            self._view = GL.glGetUniformLocation(program, 'view')
            self._floor_y = GL.glGetUniformLocation(program, 'floorY')
            self._object_has_reflection = GL.glGetUniformLocation(program, 'objectHasReflection')
            self._position = GL.glGetUniformLocation(program, "objectPosition")
            self._rotation = GL.glGetUniformLocation(program, "objectRotation")
            self ._scale = GL.glGetUniformLocation(program, "objectScale")
            self._normal_mode = GL.glGetUniformLocation(program, "normalMode")
            self._stripe_clip_start = GL.glGetUniformLocation(program, "stripeClipStart")
            self._stripe_clip_stop = GL.glGetUniformLocation(program, "stripeClipStop")
            self._material_ambient = GL.glGetUniformLocation(program, "materialAmbient")
            self._material_diffuse = GL.glGetUniformLocation(program, "materialDiffuse")
            self._material_specular = GL.glGetUniformLocation(program, "materialSpecular")
            self._material_shininess = GL.glGetUniformLocation(program, "materialShininess")
            self._material_emissive = GL.glGetUniformLocation(program, "materialEmissive")
            self._emissive_rim_power = GL.glGetUniformLocation(program, "emissiveRimPower")
            self._emissive_rim_intensity = GL.glGetUniformLocation(program, "emissiveRimIntensity")
            self._light_position = GL.glGetUniformLocation(program, "lightPosition")
            self._light_ambient = GL.glGetUniformLocation(program, "lightAmbient")
            self._light_diffuse = GL.glGetUniformLocation(program, "lightDiffuse")
            self._light_specular = GL.glGetUniformLocation(program, "lightSpecular")
            self._headlight_position = GL.glGetUniformLocation(program, "headlightPosition")
            self._headlight_direction = GL.glGetUniformLocation(program, "headlightDirection")
            self._headlight_diffuse = GL.glGetUniformLocation(program, "headlightDiffuse")
            self._headlight_diameter = GL.glGetUniformLocation(program, "headlightDiameter")
            self._headlight_enabled = GL.glGetUniformLocation(program, "headlightEnabled")
            self._show_depth = GL.glGetUniformLocation(program, "showDepth")

    @property
    def position(self):
        raise NotImplementedError

    @position.setter
    def position(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._position, *value)

    @property
    def rotation(self):
        raise NotImplementedError

    @rotation.setter
    def rotation(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._rotation, *value)

    @property
    def scale(self):
        raise NotImplementedError

    @scale.setter
    def scale(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._scale, *value)

    @property
    def normal_mode(self):
        raise NotImplementedError

    @normal_mode.setter
    def normal_mode(self, value: int):
        GL.glUniform1i(self._normal_mode, value)

    @property
    def view_position(self):
        raise NotImplementedError

    @view_position.setter
    def view_position(self, value:np.ndarray):
        GL.glUniform3fv(self._view_position, 1, value)

    @property
    def projection(self):
        raise NotImplementedError

    @projection.setter
    def projection(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._projection, 1, GL.GL_TRUE, value)

    @property
    def view(self):
        raise NotImplementedError

    @view.setter
    def view(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._view, 1, GL.GL_TRUE, value)

    @property
    def show_depth(self):
        raise NotImplementedError

    @show_depth.setter
    def show_depth(self, value: bool):
        GL.glUniform1i(self._show_depth, int(value))

    @property
    def floor_y(self):
        raise NotImplementedError

    @floor_y.setter
    def floor_y(self, value: float):
        GL.glUniform1f(self._floor_y, value)

    @property
    def has_reflection(self):
        raise NotImplementedError

    @has_reflection.setter
    def has_reflection(self, value: int):
        GL.glUniform1i(self._object_has_reflection, value)

    @property
    def stripe_clip_start(self):
        raise NotImplementedError

    @stripe_clip_start.setter
    def stripe_clip_start(self, value: float):
        GL.glUniform1f(self._stripe_clip_start, value)

    @property
    def stripe_clip_stop(self):
        raise NotImplementedError

    @stripe_clip_stop.setter
    def stripe_clip_stop(self, value: float):
        GL.glUniform1f(self._stripe_clip_stop, value)

    @property
    def material_ambient(self):
        raise NotImplementedError

    @material_ambient.setter
    def material_ambient(self, value: np.ndarray):
        GL.glUniform4fv(self._material_ambient, 1, value)

    @property
    def material_diffuse(self):
        raise NotImplementedError

    @material_diffuse.setter
    def material_diffuse(self, value: np.ndarray):
        GL.glUniform4fv(self._material_diffuse, 1, value)

    @property
    def material_specular(self):
        raise NotImplementedError

    @material_specular.setter
    def material_specular(self, value: np.ndarray):
        GL.glUniform4fv(self._material_specular, 1, value)

    @property
    def material_shininess(self):
        raise NotImplementedError

    @material_shininess.setter
    def material_shininess(self, value: float):
        GL.glUniform1f(self._material_shininess, value)

    @property
    def material_emissive(self):
        raise NotImplementedError

    @material_emissive.setter
    def material_emissive(self, value: np.ndarray):
        GL.glUniform4fv(self._material_emissive, 1, value)

    @property
    def emissive_rim_power(self):
        raise NotImplementedError

    @emissive_rim_power.setter
    def emissive_rim_power(self, value: float):
        GL.glUniform1f(self._emissive_rim_power, value)

    @property
    def emissive_rim_intensity(self):
        raise NotImplementedError

    @emissive_rim_intensity.setter
    def emissive_rim_intensity(self, value: float):
        GL.glUniform1f(self._emissive_rim_intensity, value)

    @property
    def light_position(self):
        raise NotImplementedError

    @light_position.setter
    def light_position(self, value: np.ndarray):
        GL.glUniform3fv(self._light_position, 1, value)

    @property
    def light_ambient(self):
        raise NotImplementedError

    @light_ambient.setter
    def light_ambient(self, value: np.ndarray):
        GL.glUniform4fv(self._light_ambient, 1, value)

    @property
    def light_diffuse(self):
        raise NotImplementedError

    @light_diffuse.setter
    def light_diffuse(self, value: np.ndarray):
        GL.glUniform4fv(self._light_diffuse, 1, value)

    @property
    def light_specular(self):
        raise NotImplementedError

    @light_specular.setter
    def light_specular(self, value: np.ndarray):
        GL.glUniform4fv(self._light_specular, 1, value)

    @property
    def headlight_position(self):
        raise NotImplementedError

    @headlight_position.setter
    def headlight_position(self, value: np.ndarray):
        GL.glUniform3fv(self._headlight_position, 1, value)

    @property
    def headlight_direction(self):
        raise NotImplementedError

    @headlight_direction.setter
    def headlight_direction(self, value: np.ndarray):
        GL.glUniform3fv(self._headlight_direction, 1, value)

    @property
    def headlight_diffuse(self):
        raise NotImplementedError

    @headlight_diffuse.setter
    def headlight_diffuse(self, value: np.ndarray):
        GL.glUniform4fv(self._headlight_diffuse, 1, value)

    @property
    def headlight_diameter(self):
        raise NotImplementedError

    @headlight_diameter.setter
    def headlight_diameter(self, value: float):
        GL.glUniform1f(self._headlight_diameter, value)

    @property
    def headlight_enabled(self):
        raise NotImplementedError

    @headlight_enabled.setter
    def headlight_enabled(self, value: int):
        GL.glUniform1i(self._headlight_enabled, value)


class EdgesProgram(Program):

    def __init__(self):
        program = _edges.compile_program()
        super().__init__(program)

        with self:
            self._projection = GL.glGetUniformLocation(program, 'projection')
            self._view = GL.glGetUniformLocation(program, 'view')
            self._position = GL.glGetUniformLocation(program, "objectPosition")
            self._rotation = GL.glGetUniformLocation(program, "objectRotation")
            self ._scale = GL.glGetUniformLocation(program, "objectScale")
            self._normal_mode = GL.glGetUniformLocation(program, "normalMode")
            self._render_mode = GL.glGetUniformLocation(program, "renderMode")
            self._normal_length = GL.glGetUniformLocation(program, "normalLength")
            self._stripe_clip_start = GL.glGetUniformLocation(program, "stripeClipStart")
            self._stripe_clip_stop = GL.glGetUniformLocation(program, "stripeClipStop")
            self._material_ambient = GL.glGetUniformLocation(program, "materialAmbient")
            self._material_diffuse = GL.glGetUniformLocation(program, "materialDiffuse")
            self._material_specular = GL.glGetUniformLocation(program, "materialSpecular")
            self._material_shininess = GL.glGetUniformLocation(program, "materialShininess")
            self._material_emissive = GL.glGetUniformLocation(program, "materialEmissive")

    @property
    def position(self):
        raise NotImplementedError

    @position.setter
    def position(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._position, *value)

    @property
    def rotation(self):
        raise NotImplementedError

    @rotation.setter
    def rotation(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._rotation, *value)

    @property
    def scale(self):
        raise NotImplementedError

    @scale.setter
    def scale(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._scale, *value)

    @property
    def normal_mode(self):
        raise NotImplementedError

    @normal_mode.setter
    def normal_mode(self, value: int):
        GL.glUniform1i(self._normal_mode, value)

    @property
    def normal_length(self):
        raise NotImplementedError

    @normal_length.setter
    def normal_length(self, value: float):
        GL.glUniform1f(self._normal_length, value)

    @property
    def render_mode(self):
        raise NotImplementedError

    @render_mode.setter
    def render_mode(self, value: int):
        GL.glUniform1i(self._render_mode, value)

    @property
    def projection(self):
        raise NotImplementedError

    @projection.setter
    def projection(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._projection, 1, GL.GL_TRUE, value)

    @property
    def view(self):
        raise NotImplementedError

    @view.setter
    def view(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._view, 1, GL.GL_TRUE, value)

    @property
    def stripe_clip_start(self):
        raise NotImplementedError

    @stripe_clip_start.setter
    def stripe_clip_start(self, value: float):
        GL.glUniform1f(self._stripe_clip_start, value)

    @property
    def stripe_clip_stop(self):
        raise NotImplementedError

    @stripe_clip_stop.setter
    def stripe_clip_stop(self, value: float):
        GL.glUniform1f(self._stripe_clip_stop, value)

    @property
    def material_ambient(self):
        raise NotImplementedError

    @material_ambient.setter
    def material_ambient(self, value: np.ndarray):
        GL.glUniform4fv(self._material_ambient, 1, value)

    @property
    def material_diffuse(self):
        raise NotImplementedError

    @material_diffuse.setter
    def material_diffuse(self, value: np.ndarray):
        GL.glUniform4fv(self._material_diffuse, 1, value)

    @property
    def material_specular(self):
        raise NotImplementedError

    @material_specular.setter
    def material_specular(self, value: np.ndarray):
        GL.glUniform4fv(self._material_specular, 1, value)

    @property
    def material_shininess(self):
        raise NotImplementedError

    @material_shininess.setter
    def material_shininess(self, value: float):
        GL.glUniform1f(self._material_shininess, value)

    @property
    def material_emissive(self):
        raise NotImplementedError

    @material_emissive.setter
    def material_emissive(self, value: np.ndarray):
        GL.glUniform4fv(self._material_emissive, 1, value)


class VerticesProgram(Program):

    def __init__(self):
        program = _vertices.compile_program()
        super().__init__(program)

        with self:
            self._projection = GL.glGetUniformLocation(program, 'projection')
            self._view = GL.glGetUniformLocation(program, 'view')
            self._position = GL.glGetUniformLocation(program, "objectPosition")
            self._rotation = GL.glGetUniformLocation(program, "objectRotation")
            self._scale = GL.glGetUniformLocation(program, "objectScale")
            self._color = GL.glGetUniformLocation(program, "vertexColor")
            self._stripe_clip_start = GL.glGetUniformLocation(program, "stripeClipStart")
            self._stripe_clip_stop = GL.glGetUniformLocation(program, "stripeClipStop")

    @property
    def position(self):
        raise NotImplementedError

    @position.setter
    def position(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._position, *value)

    @property
    def rotation(self):
        raise NotImplementedError

    @rotation.setter
    def rotation(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._rotation, *value)

    @property
    def scale(self):
        raise NotImplementedError

    @scale.setter
    def scale(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._scale, *value)

    @property
    def color(self):
        raise NotImplementedError

    @color.setter
    def color(self, value: list[float, float, float]):
        GL.glUniform3f(self._color, *value)

    @property
    def projection(self):
        raise NotImplementedError

    @projection.setter
    def projection(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._projection, 1, GL.GL_TRUE, value)

    @property
    def view(self):
        raise NotImplementedError

    @view.setter
    def view(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._view, 1, GL.GL_TRUE, value)

    @property
    def stripe_clip_start(self):
        raise NotImplementedError

    @stripe_clip_start.setter
    def stripe_clip_start(self, value: float):
        GL.glUniform1f(self._stripe_clip_start, value)

    @property
    def stripe_clip_stop(self):
        raise NotImplementedError

    @stripe_clip_stop.setter
    def stripe_clip_stop(self, value: float):
        GL.glUniform1f(self._stripe_clip_stop, value)


class GridProgram(Program):

    def __init__(self):
        program = _grid2d.compile_program()
        super().__init__(program)

        with self:
            self._projection = GL.glGetUniformLocation(program, "projection")
            self._spacing = GL.glGetUniformLocation(program, "uSpacing")
            self._world_per_pixel = GL.glGetUniformLocation(program, "uWorldPerPixel")
            self._dot_color = GL.glGetUniformLocation(program, "uDotColor")

    @property
    def projection(self):
        raise NotImplementedError

    @projection.setter
    def projection(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._projection, 1, GL.GL_FALSE,
                              np.ascontiguousarray(value))

    @property
    def spacing(self):
        raise NotImplementedError

    @spacing.setter
    def spacing(self, value: float):
        GL.glUniform1f(self._spacing, value)

    @property
    def world_per_pixel(self):
        raise NotImplementedError

    @world_per_pixel.setter
    def world_per_pixel(self, value: float):
        GL.glUniform1f(self._world_per_pixel, value)

    @property
    def dot_color(self):
        raise NotImplementedError

    @dot_color.setter
    def dot_color(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._dot_color, *value)


class FloorProgram(Program):

    def __init__(self):
        program = _floor.compile_program()
        super().__init__(program)

        with self:
            self._mvp = GL.glGetUniformLocation(program, 'uMVP')
            self._tile_size = GL.glGetUniformLocation(program, 'uTileSize')
            self._minor_spacing = GL.glGetUniformLocation(program, 'uMinorSpacing')
            self._color_a = GL.glGetUniformLocation(program, 'uColorA')
            self._color_b = GL.glGetUniformLocation(program, 'uColorB')
            self._major_color = GL.glGetUniformLocation(program, 'uMajorColor')
            self._minor_color = GL.glGetUniformLocation(program, 'uMinorColor')
            self._major_width = GL.glGetUniformLocation(program, 'uMajorWidth')
            self._minor_width = GL.glGetUniformLocation(program, 'uMinorWidth')
            self._stipple_pattern = GL.glGetUniformLocation(program, 'uStipplePattern')
            self._has_minor_grid = GL.glGetUniformLocation(program, 'uHasMinorGrid')
            self._stipple_phase = GL.glGetUniformLocation(program, 'uStipplePhase')
            self._opaque_pass = GL.glGetUniformLocation(program, 'uOpaquePass')

    @property
    def mvp(self):
        raise NotImplementedError

    @mvp.setter
    def mvp(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._mvp, 1, GL.GL_TRUE, value)

    @property
    def tile_size(self):
        raise NotImplementedError

    @tile_size.setter
    def tile_size(self, value: float):
        GL.glUniform1f(self._tile_size, value)

    @property
    def minor_spacing(self):
        raise NotImplementedError

    @minor_spacing.setter
    def minor_spacing(self, value: float):
        GL.glUniform1f(self._minor_spacing, value)

    @property
    def color_a(self):
        raise NotImplementedError

    @color_a.setter
    def color_a(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._color_a, *value)

    @property
    def color_b(self):
        raise NotImplementedError

    @color_b.setter
    def color_b(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._color_b, *value)

    @property
    def major_color(self):
        raise NotImplementedError

    @major_color.setter
    def major_color(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._major_color, *value)

    @property
    def minor_color(self):
        raise NotImplementedError

    @minor_color.setter
    def minor_color(self, value: list[float, float, float, float]):
        GL.glUniform4f(self._minor_color, *value)

    @property
    def major_width(self):
        raise NotImplementedError

    @major_width.setter
    def major_width(self, value: float):
        GL.glUniform1f(self._major_width, value)

    @property
    def minor_width(self):
        raise NotImplementedError

    @minor_width.setter
    def minor_width(self, value: float):
        GL.glUniform1f(self._minor_width, value)

    @property
    def stipple_pattern(self):
        raise NotImplementedError

    @stipple_pattern.setter
    def stipple_pattern(self, value: int):
        GL.glUniform1ui(self._stipple_pattern, value & 0xFFFFFFFF)

    @property
    def has_minor_grid(self):
        raise NotImplementedError

    @has_minor_grid.setter
    def has_minor_grid(self, value: int):
        GL.glUniform1ui(self._has_minor_grid, value)

    @property
    def stipple_phase(self):
        raise NotImplementedError

    @stipple_phase.setter
    def stipple_phase(self, value: int):
        GL.glUniform1ui(self._stipple_phase, value)

    @property
    def opaque_pass(self):
        raise NotImplementedError

    @opaque_pass.setter
    def opaque_pass(self, value: int):
        GL.glUniform1i(self._opaque_pass, value)


class TextureProgram(Program):
    """
    Unlit textured-quad shader -- see ``gl.shaders.texture`` for the
    GLSL and why this exists (peg-board floating wire tables, captured
    off-screen from a real Qt widget and uploaded as a GL texture).
    """

    def __init__(self):
        program = _texture.compile_program()
        super().__init__(program)

        with self:
            self._projection = GL.glGetUniformLocation(program, 'projection')
            self._view = GL.glGetUniformLocation(program, 'view')
            self._position = GL.glGetUniformLocation(program, 'objectPosition')
            self._scale = GL.glGetUniformLocation(program, 'objectScale')
            self._image_texture = GL.glGetUniformLocation(program, 'imageTexture')
            self._quad_size_px = GL.glGetUniformLocation(program, 'quadSizePx')
            self._corner_radius_px = GL.glGetUniformLocation(program, 'cornerRadiusPx')
            self._ring_thickness_px = GL.glGetUniformLocation(program, 'ringThicknessPx')
            self._bottom_corner_trim_px = GL.glGetUniformLocation(program, 'bottomCornerTrimPx')
            GL.glUniform1i(self._image_texture, 0)  # always texture unit 0

    @property
    def projection(self):
        raise NotImplementedError

    @projection.setter
    def projection(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._projection, 1, GL.GL_TRUE, value)

    @property
    def view(self):
        raise NotImplementedError

    @view.setter
    def view(self, value: np.ndarray):
        GL.glUniformMatrix4fv(self._view, 1, GL.GL_TRUE, value)

    @property
    def position(self):
        raise NotImplementedError

    @position.setter
    def position(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._position, *value)

    @property
    def scale(self):
        raise NotImplementedError

    @scale.setter
    def scale(self, value: tuple[float, float, float]):
        GL.glUniform3f(self._scale, *value)

    @property
    def rotation(self):
        raise NotImplementedError

    @rotation.setter
    def rotation(self, value: list[float, float, float, float]):
        # No-op -- a peg-board table quad is never rotated, but
        # VBOHandlerBase.render() unconditionally sets program.rotation,
        # so this has to exist as a real (if unused) property, same as
        # the scratch prototype's own TextureProgram this was ported
        # from already established.
        pass

    @property
    def quad_size_px(self):
        raise NotImplementedError

    @quad_size_px.setter
    def quad_size_px(self, value: tuple[float, float]):
        """Pixel size of the captured widget this quad displays --
        ``objects_pegboard.pegboard_table.PegboardTable`` sets this from
        its own ``_texture_px_size`` every time it re-grabs, so the
        fragment shader's rounded-corner clip (see ``cornerRadiusPx``)
        can convert its normalized UV into real pixels and get a
        consistent radius regardless of how big the captured widget is.
        """
        GL.glUniform2f(self._quad_size_px, *value)

    @property
    def corner_radius_px(self):
        raise NotImplementedError

    @corner_radius_px.setter
    def corner_radius_px(self, value: tuple[float, float, float, float]):
        """Per-corner radius, in the SAME pixel units as
        ``quad_size_px`` -- ``(top-left, top-right, bottom-right,
        bottom-left)``, each 0 disabling clipping on that one corner
        (all 4 zero draws a plain rectangle). See ``fragment.frag``'s
        own ``roundedRectDist``. The peg-board table's own quad leaves
        this at all 0s (its earlier native-chrome-rounding workaround
        turned out to be a mispositioned capture rect letting the
        QMdiArea's own gray background bleed in, not real corner
        rounding -- fixed at the capture step instead, see
        mdi_host.py); the selection border quad rounds only its top 2
        corners, matching the table's own native top-corner rounding
        (Kevin, 2026-09-16).
        """
        GL.glUniform4f(self._corner_radius_px, *value)

    @property
    def ring_thickness_px(self):
        raise NotImplementedError

    @ring_thickness_px.setter
    def ring_thickness_px(self, value: float):
        """0 (default) draws a normal filled rounded rect. >0 instead
        keeps only a ring this many units wide along the inside of the
        outer rounded-rect boundary -- see ``fragment.frag``'s own
        comment for why the selection border uses this rather than
        relying on the table's own opaque draw to punch a hole through
        a plain filled quad.
        """
        GL.glUniform1f(self._ring_thickness_px, float(value))

    @property
    def bottom_corner_trim_px(self):
        raise NotImplementedError

    @bottom_corner_trim_px.setter
    def bottom_corner_trim_px(self, value: float):
        """Size (same units as ``quad_size_px``) of a plain square
        notch discarded at ONLY the bottom-left/bottom-right corners --
        0 disables it. See ``fragment.frag``'s own comment for why:
        the peg-board table's captured native chrome leaves a faint
        curved line right at those two (otherwise square) corners.
        """
        GL.glUniform1f(self._bottom_corner_trim_px, float(value))

