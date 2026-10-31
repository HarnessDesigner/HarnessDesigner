# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A plain-Python snapshot of ``Config.ray_trace`` for one render.

``Config`` is database backed, so it is only read on the thread that starts
a render; the worker thread then works from this snapshot and never touches
the database.
"""

from dataclasses import dataclass, field

from .. import config as _config
from .. import check_types as _check_types


Config = _config.Config.ray_trace

_FALLBACK_RESOLUTION = (1920, 1080)


@dataclass
class RenderSettings:
    """Everything a render needs from ``Config.ray_trace``, copied by value."""

    width: int = _FALLBACK_RESOLUTION[0]
    height: int = _FALLBACK_RESOLUTION[1]
    ambient_intensity: float = 0.2
    background_color1: tuple[float, float, float] = (0.18, 0.20, 0.22)
    background_color2: tuple[float, float, float] = (0.18, 0.20, 0.22)
    enable_gradient: bool = True
    enable_environment_map: bool = True
    generate_environment_map: bool = True
    environment_map_path: str = ''
    enable_reflections: bool = True
    enable_shadows: bool = True
    shadow_softness: float = 1.0
    enable_ambient_occlusion: bool = False
    ambient_occlusion_samples: int = 8
    ambient_occlusion_radius: float = 0.5
    enable_depth_of_field: bool = False

    camera_light: bool = True

    # The 3D editor's floor (``Config.editor_3d.floor``), as the kernel's ``floor_params``: enable, y,
    # half size, tile size, minor spacing, has minor, major width, minor width, then the RGBA of
    # tile A, tile B, major line and minor line. The dash pattern needs all 32 bits, which a float
    # can't hold, so it and its phase are separate.
    floor_enabled: bool = False
    floor_params: tuple[float, ...] = ()
    floor_stipple_pattern: int = 0
    floor_stipple_phase: int = 0

    # Each light is (position, intensity, color).
    lights: list[tuple[tuple[float, float, float], float, tuple[float, float, float]]] = field(default_factory=list)

    @classmethod
    @_check_types.do
    def from_config(cls) -> "RenderSettings":
        """Copy the current ``Config.ray_trace`` values.

        :returns: A snapshot that is safe to hand to a worker thread.
        :rtype: RenderSettings
        """
        width, height = _FALLBACK_RESOLUTION

        for res in Config.resolutions:
            if res['label'] == Config.default_resolution:
                width = int(res['width'])
                height = int(res['height'])
                break

        lights = []
        for light in Config.lighting.lights:
            lights.append((
                tuple(float(item) for item in light['position']),
                float(light['intensity']),
                tuple(float(item) for item in light['color'])
            ))

        settings = cls(
            width=width,
            height=height,
            ambient_intensity=float(Config.lighting.ambient_intensity),
            background_color1=tuple(float(item) for item in Config.background.color1),
            background_color2=tuple(float(item) for item in Config.background.color2),
            enable_gradient=bool(Config.background.enable_gradient),
            enable_environment_map=bool(Config.environment_map.enable),
            generate_environment_map=bool(Config.environment_map.generate),
            environment_map_path=str(Config.environment_map.path or ''),
            enable_reflections=bool(Config.enable_reflections),
            enable_shadows=bool(Config.shadows.enable),
            shadow_softness=float(Config.shadows.softness),
            enable_ambient_occlusion=bool(Config.ambient_occlusion.enable),
            ambient_occlusion_samples=int(Config.ambient_occlusion.samples),
            ambient_occlusion_radius=float(Config.ambient_occlusion.radius),
            enable_depth_of_field=bool(Config.enable_depth_of_field),
            camera_light=bool(Config.lighting.camera_light),
            lights=lights
        )

        if Config.match_viewport:
            settings._match_viewport()

        return settings

    @_check_types.do
    def _match_viewport(self) -> None:
        """Take the background and floor from the 3D editor, as the viewport shows them.

        The background becomes the editor's flat colour (no gradient, no environment map) and the
        floor is described for the kernel when the editor shows one.
        """
        editor = _config.Config.editor_3d

        background = tuple(float(item) for item in editor.background_color[:3])
        self.background_color1 = background
        self.background_color2 = background
        self.enable_gradient = False
        self.enable_environment_map = False

        floor = editor.floor
        if not floor.enable:
            return

        grid = floor.grid
        tile = float(grid.size)

        self.floor_enabled = True
        self.floor_params = (
            1.0,
            float(floor.ground_height),
            float(floor.size) / 2.0,
            tile,
            tile / (float(grid.secondary_lines_per_tile) + 1.0),
            1.0 if grid.enable else 0.0,
            float(grid.primary_line_width),
            float(grid.secondary_line_width),
            *(float(item) for item in grid.primary_color),
            *(float(item) for item in grid.secondary_color),
            *(float(item) for item in grid.primary_line_color),
            *(float(item) for item in grid.secondary_line_color)
        )
        self.floor_stipple_pattern = int(grid.secondary_line_pattern) & 0xFFFFFFFF
        self.floor_stipple_phase = int(bool(grid.secondary_line_shift))
