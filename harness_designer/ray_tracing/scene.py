# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Scene assembly helpers for preparing geometry and lighting for ray tracing."""

from typing import TYPE_CHECKING, Protocol
from dataclasses import dataclass

import math

from PIL import Image
import numpy as np

from . import bvh_processor as _bvh_processor
from . import light as _light
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..gl.canvas_3d import camera as _camera
    from ..geometry import angle as _angle
    from ..geometry import point as _point
    from ..gl.materials import material as _gl_materials
    from ..gl import vbo as _vbo
    from . import settings as _settings


# Vertical field of view of the 3D canvas's projection (``gl.canvas_3d.canvas.FOV_DEGREES``); only used
# before the canvas has drawn a frame and the camera has no value yet.
DEFAULT_FIELD_OF_VIEW = 65.0

# Size of the generated sky; it is only sampled by direction, so it does not
# need to follow the render resolution.
GENERATED_ENVIRONMENT_SIZE = (1024, 512)


@_check_types.do
def visible_field_of_view(canvas_size: tuple[int, int], window_size: tuple[int, int],
                          fov: float) -> tuple[float, float]:
    """Work out what part of the 3D canvas the user can actually see.

    The canvas is a fixed, oversized GL surface whose projection has a vertical
    field of view of ``fov`` over its whole height; the window around it is
    smaller and shows a centred crop (``CanvasWindowBase``). Pixels are square,
    so the crop's field of view follows from its share of the canvas height.

    :param canvas_size: ``(width, height)`` of the canvas, the "virtual size".
    :type canvas_size: tuple[int, int]
    :param window_size: ``(width, height)`` of the window that shows it.
    :type window_size: tuple[int, int]
    :param fov: Vertical field of view of the whole canvas, degrees.
    :type fov: float
    :returns: ``(vertical field of view in degrees, width / height)`` of the visible crop.
    :rtype: tuple[float, float]
    """
    canvas_w, canvas_h = canvas_size
    window_w, window_h = window_size

    # A window larger than the canvas shows nothing beyond the canvas.
    visible_w = min(canvas_w, window_w)
    visible_h = min(canvas_h, window_h)

    if min(canvas_w, canvas_h, visible_w, visible_h) <= 0:
        return fov, (canvas_w / canvas_h if canvas_h > 0 else 1.0)

    tan_half = math.tan(math.radians(fov) / 2.0) * visible_h / canvas_h
    return math.degrees(2.0 * math.atan(tan_half)), visible_w / visible_h


@_check_types.do
def fit_field_of_view(fov: float, view_aspect: float | None, image_aspect: float) -> float:
    """Widen a vertical field of view so an image shows all of a view.

    ``fov`` frames a view of aspect ``view_aspect`` top to bottom. An image at
    least as wide as the view keeps that, and shows a bit more at the sides. A
    narrower image would lose the view's sides, so it is framed to the view's
    width instead and shows a bit more above and below.

    :param fov: Vertical field of view of the view, degrees.
    :type fov: float
    :param view_aspect: Width / height of the view, or ``None`` when unknown.
    :type view_aspect: float | None
    :param image_aspect: Width / height of the image being rendered.
    :type image_aspect: float
    :returns: Vertical field of view for the image, degrees.
    :rtype: float
    """
    if view_aspect is None or image_aspect <= 0 or image_aspect >= view_aspect:
        return fov

    tan_half = math.tan(math.radians(fov) / 2.0) * view_aspect / image_aspect
    return math.degrees(2.0 * math.atan(tan_half))


def _clip_polygon(polygon: list[np.ndarray], z: float, keep_above: bool) -> list[np.ndarray]:
    """Cut a convex polygon with the plane ``Z == z`` (Sutherland-Hodgman), keeping one side.

    :param polygon: Corners, each a length 3 array.
    :param z: Where to cut.
    :param keep_above: Keep the ``Z >= z`` side if true, the ``Z <= z`` side otherwise.
    :returns: The corners of what is kept; empty when nothing is.
    """
    def kept(point: np.ndarray) -> bool:
        return point[2] >= z if keep_above else point[2] <= z

    result = []

    for i, current in enumerate(polygon):
        previous = polygon[i - 1]

        if kept(current) != kept(previous):
            t = (z - previous[2]) / (current[2] - previous[2])
            result.append(previous + (current - previous) * t)

        if kept(current):
            result.append(current)

    return result


class SceneObject(Protocol):
    """What :meth:`Scene.add_object` reads from each object added to a scene."""

    vbo: "_vbo.VBOHandlerBase | None"
    position: "_point.Point"
    angle: "_angle.Angle"
    scale: "_point.Point"
    material: "_gl_materials.GLMaterial"

    # Optional. Objects drawn as several placements of one mesh (wires and
    # bundles) provide this: an iterable of (position, angle, scale, material),
    # plus (window, vbo) on the end for a windowed mesh (a wire's stripe).
    # Without it, the four attributes above are the single placement.
    # def ray_trace_parts(self) -> Iterable[tuple]: ...


@dataclass
class SceneData:
    """The flattened arrays :class:`~.renderer.Renderer` uploads to the GPU."""

    vertices: np.ndarray        # (N, 3) float32, world space
    faces: np.ndarray           # (M, 3) int32
    bvh_bounds: np.ndarray      # float32, 6 per node
    bvh_structure: np.ndarray   # int32, 4 per node
    bvh_indices: np.ndarray     # int32, triangle order used by the leaves
    object_ids: np.ndarray      # (M,) int32, row of ``materials`` for each face
    materials: np.ndarray       # (K, 12) float32
    lights: np.ndarray          # (L, 7) float32
    environment_map: np.ndarray | None  # (H, W, 3) uint8


class Scene:

    """Collect camera state, scene objects, materials, and lighting for the ray-tracing renderer.

    Objects are read in :meth:`add_object` (on the GUI thread, where it is safe
    to touch them) and :meth:`build` does the rest, so it can run on a worker
    thread.
    """
    @_check_types.do
    def __init__(self, settings: "_settings.RenderSettings", camera: "_camera.Camera",
                 canvas_size: tuple[int, int] | None = None, window_size: tuple[int, int] | None = None):
        """Initialize the object and capture the state required for later interaction.

        :param settings: Snapshot of the render settings.
        :type settings: RenderSettings
        :param camera: Active 3D camera used to resolve the view.
        :type camera: "_camera.Camera"
        :param canvas_size: ``(width, height)`` of the 3D canvas's fixed virtual surface.
        :type canvas_size: tuple[int, int] | None
        :param window_size: ``(width, height)`` of the window showing that surface. With both sizes
            the render frames only what the window shows (see :func:`visible_field_of_view`);
            without them, the camera's whole field of view.
        :type window_size: tuple[int, int] | None
        """
        self.settings = settings
        self.width = settings.width
        self.height = settings.height

        self.camera_origin = np.array(camera.position.as_numpy, dtype=np.float32)
        self.camera_target = np.array(camera.focal_position.as_numpy, dtype=np.float32)
        self.camera_up = np.array(camera.up, dtype=np.float32)

        # The camera reports 0.0 until the canvas has drawn its first frame.
        fov = float(camera.field_of_view) or DEFAULT_FIELD_OF_VIEW
        view_aspect = None

        if canvas_size and window_size:
            fov, view_aspect = visible_field_of_view(canvas_size, window_size, fov)

        self.fov = fit_field_of_view(fov, view_aspect, self.width / self.height)

        self._vertices: list[np.ndarray] = []
        self._materials: list[np.ndarray] = []

    @property
    @_check_types.do
    def object_count(self) -> int:
        """Number of objects that contributed geometry.

        :rtype: int
        """
        return len(self._vertices)

    @_check_types.do
    def add_object(self, obj: "SceneObject") -> bool:
        """Copy an object's mesh into world space and keep it for :meth:`build`.

        The mesh is read from the object's VBO handler, which holds it in
        local space as a triangle soup (three vertices per triangle, no index
        buffer); position, angle and scale are applied here the same way
        ``BaseVar._compute_aabb`` applies them.

        Most objects are one placement of their mesh. A wire or bundle is a
        chain of straight tubes, one per segment of its path, all sharing the
        one cylinder mesh: those objects list their placements in
        ``ray_trace_parts()`` and each becomes its own copy of the mesh. A part
        is ``(position, angle, scale, material)``, or for a windowed mesh
        (a wire's stripe) ``(position, angle, scale, material, (start, stop),
        vbo)``; see :meth:`_add_windowed`. An object whose ``ray_trace_parts()``
        yields nothing adds nothing.

        :param obj: Object to include in the render.
        :type obj: SceneObject
        :returns: ``False`` when the object has no triangles to render.
        :rtype: bool
        """
        # What the viewport does not draw (hidden objects, snap probes) is not rendered either.
        if not getattr(obj, 'is_visible', True):
            return False

        get_parts = getattr(obj, 'ray_trace_parts', None)
        if get_parts is None:
            parts = ((obj.position, obj.angle, obj.scale, obj.material),)
        else:
            parts = get_parts()

        meshes: dict[int, np.ndarray | None] = {}
        added = False

        for position, angle, scale, material, *extra in parts:
            window = extra[0] if extra else None
            vbo = extra[1] if len(extra) > 1 else obj.vbo

            key = id(vbo)
            if key not in meshes:
                meshes[key] = self._local_mesh(vbo)

            local = meshes[key]
            if local is None:
                continue

            if window is None:
                vertices = local * scale.as_numpy
            else:
                vertices = self._add_windowed(local, scale, window)
                if vertices is None:
                    continue

            vertices @= angle
            vertices += position.as_numpy

            self._vertices.append(vertices)
            self._materials.append(material.cl_array)
            added = True

        return added

    @staticmethod
    @_check_types.do
    def _local_mesh(vbo: "_vbo.VBOHandlerBase | None") -> np.ndarray | None:
        """Return a VBO's local-space triangle soup as ``(N, 3)`` float32.

        :param vbo: The VBO handler.
        :type vbo: VBOHandlerBase | None
        :returns: The vertices, or ``None`` when there are no whole triangles.
        :rtype: numpy.ndarray | None
        """
        data = getattr(vbo, 'vertices', None)
        if data is None:
            return None

        count = len(data) // 9 * 9
        if not count:
            return None

        return np.array(data[:count], dtype=np.float32).reshape(-1, 3)

    @staticmethod
    @_check_types.do
    def _add_windowed(local: np.ndarray, scale: "_point.Point", window: tuple[float, float]) -> np.ndarray | None:
        """Cut a shared mesh down to a window along its local Z and place it.

        This is what the faces vertex shader does for a wire's stripe
        (``stripeClipStart`` / ``stripeClipStop``): the helix mesh's local Z is
        in real units, so only X and Y are scaled, Z is re-based so the window
        starts at 0, and everything outside the window is dropped. A triangle
        that crosses the window's edge is cut exactly at it. (Keeping whole
        triangles instead overshoots by several mm: the helix's triangles are
        long, and the overshoot would poke past the end of a segment at a bend.)

        :param local: ``(N, 3)`` triangle soup, local space.
        :type local: numpy.ndarray
        :param scale: Only X and Y are used.
        :type scale: Point
        :param window: ``(start, stop)`` along local Z.
        :type window: tuple[float, float]
        :returns: Scaled, re-based vertices ready for the angle and position, or ``None`` when nothing is inside.
        :rtype: numpy.ndarray | None
        """
        start, stop = window

        triangles = local.reshape(-1, 3, 3)
        low = triangles[:, :, 2].min(axis=1)
        high = triangles[:, :, 2].max(axis=1)

        inside = (low >= start) & (high <= stop)
        crossing = ~inside & (high >= start) & (low <= stop)

        pieces = [triangles[inside].reshape(-1, 3)]

        for triangle in triangles[crossing]:
            polygon = _clip_polygon(list(triangle), start, keep_above=True)
            polygon = _clip_polygon(polygon, stop, keep_above=False)

            # A convex polygon is cut into a fan of triangles from its first corner.
            for i in range(1, len(polygon) - 1):
                pieces.append(np.array((polygon[0], polygon[i], polygon[i + 1]), dtype=np.float32))

        vertices = np.concatenate(pieces)
        if not len(vertices):
            return None

        vertices = vertices.astype(np.float32, copy=True)
        vertices[:, 0] *= scale.x
        vertices[:, 1] *= scale.y
        vertices[:, 2] -= start
        return vertices

    @_check_types.do
    def _environment_map(self) -> np.ndarray | None:
        """Return the environment map the settings ask for, if any.

        :rtype: numpy.ndarray | None
        """
        settings = self.settings

        if not settings.enable_environment_map:
            return None

        if settings.generate_environment_map or not settings.environment_map_path:
            return self.generate_environment(GENERATED_ENVIRONMENT_SIZE)

        return self.load_environment_map(settings.environment_map_path)

    @staticmethod
    @_check_types.do
    def load_environment_map(image_path: str) -> np.ndarray:
        """Load an environment map image.

        :param image_path: Path to the image file that should be loaded.
        :type image_path: str
        :returns: ``(H, W, 3)`` uint8 equirectangular image.
        :rtype: numpy.ndarray
        """
        with Image.open(image_path) as img:
            return np.ascontiguousarray(img.convert('RGB'), dtype=np.uint8)

    @staticmethod
    @_check_types.do
    def generate_environment(size: tuple[int, int]) -> np.ndarray:
        """Generate a simple sky gradient, light blue overhead fading to white.

        :param size: Requested image size as ``(width, height)``.
        :type size: tuple[int, int]
        :returns: ``(H, W, 3)`` uint8 equirectangular image.
        :rtype: numpy.ndarray
        """
        width, height = size

        top = np.array((135, 206, 235), dtype=np.float32)
        bottom = np.array((240, 240, 255), dtype=np.float32)

        t = (np.arange(height, dtype=np.float32) / height)[:, None]
        rows = top + (bottom - top) * t

        return np.ascontiguousarray(
            np.repeat(rows[:, None, :], width, axis=1), dtype=np.uint8)

    @_check_types.do
    def build(self) -> SceneData:
        """Merge every object into one mesh and build its BVH, materials and lights.

        :returns: The arrays the renderer needs.
        :rtype: SceneData
        :raises ValueError: When no object contributed geometry.
        """
        if not self._vertices:
            raise ValueError('There is nothing to render')

        vertices = np.concatenate(self._vertices)
        faces = np.arange(len(vertices), dtype=np.int32).reshape(-1, 3)

        object_ids = np.concatenate([
            np.full(len(verts) // 3, index, dtype=np.int32)
            for index, verts in enumerate(self._vertices)])

        bvh_bounds, bvh_structure, bvh_indices = _bvh_processor.build_bvh(vertices, faces)

        lights = [_light.Light(*light) for light in self.settings.lights]

        # The configured lights are fixed points in the world, and one that is inside or under the
        # model lights nothing the camera can see. A light at the camera always does, as the
        # viewport's own headlight does. With no lights at all everything would render black, so
        # one is added then whether or not it was asked for.
        if self.settings.camera_light or not lights:
            lights.insert(0, _light.Light(tuple(float(item) for item in self.camera_origin)))

        return SceneData(
            vertices=vertices,
            faces=faces,
            bvh_bounds=bvh_bounds,
            bvh_structure=bvh_structure,
            bvh_indices=bvh_indices,
            object_ids=object_ids,
            materials=np.array(self._materials, dtype=np.float32),
            lights=np.array([light.to_array() for light in lights], dtype=np.float32),
            environment_map=self._environment_map()
        )
