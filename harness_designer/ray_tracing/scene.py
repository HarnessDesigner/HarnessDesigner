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


class SceneObject(Protocol):
    """What :meth:`Scene.add_object` reads from each object added to a scene."""

    vbo: "_vbo.VBOHandlerBase | None"
    position: "_point.Point"
    angle: "_angle.Angle"
    scale: "_point.Point"
    material: "_gl_materials.GLMaterial"

    # Optional. An object that is not one placement of one mesh (a wire, a cable or a bundle: tubes along a path with rounded
    # corners) makes its own triangles and provides this: an iterable of (vertices, normals, material), world space, three corners
    # per triangle, the normals unit length (see ray_tracing/tube_mesh.py). Without it, the attributes above are the one placement.
    # def ray_trace_meshes(self) -> Iterable[tuple]: ...


@dataclass
class SceneData:
    """The flattened arrays :class:`~.renderer.Renderer` uploads to the GPU."""

    vertices: np.ndarray        # (N, 3) float32, world space
    faces: np.ndarray           # (M, 3) int32
    vertex_normals: np.ndarray | None   # (N, 3) float32, world space; zero for a vertex without one; None if nothing is smooth
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
        self._normals: list[np.ndarray | None] = []
        self._materials: list[np.ndarray] = []

        # A mesh is read from its VBO once however many objects share it (every housing of one model shares its mesh).
        # The VBO is kept in the value so its id stays unique.
        self._meshes: dict[int, tuple[object, tuple[np.ndarray, np.ndarray] | None]] = {}

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
        ``BaseVar._compute_aabb`` applies them. An object the viewport draws
        smooth (its ``smooth`` is true) also keeps the VBO's per-vertex smooth
        normals, so the renderer shades it the way the viewport does instead of
        showing the facets of a curved low-poly surface.

        A wire, a cable or a bundle is not one placement of a mesh: it is tubes along a path whose corners are
        rounded, twisted and striped, made by the viewport's shader. Those objects make the same triangles on the CPU
        (``ray_trace_meshes()``, from ``ray_tracing/tube_mesh.py``), already in world space with their smooth normals, and
        each ``(vertices, normals, material)`` they yield is added as it is. An object whose ``ray_trace_meshes()`` yields
        nothing adds nothing.

        :param obj: Object to include in the render.
        :type obj: SceneObject
        :returns: ``False`` when the object has no triangles to render.
        :rtype: bool
        """
        # What the viewport does not draw (hidden objects, snap probes) is not rendered either.
        if not getattr(obj, 'is_visible', True):
            return False

        get_meshes = getattr(obj, 'ray_trace_meshes', None)

        if get_meshes is not None:
            added = False

            for vertices, normals, material in get_meshes():
                self._vertices.append(vertices)
                self._normals.append(normals)
                self._materials.append(material.cl_array)
                added = True

            return added

        # An object with no geometry (a waypoint's layout: the route draws its own corner) adds nothing.
        if obj.vbo is None:
            return False

        key = id(obj.vbo)
        if key not in self._meshes:
            self._meshes[key] = (obj.vbo, self._local_mesh(obj.vbo))

        mesh = self._meshes[key][1]
        if mesh is None:
            return False

        local, local_normals = mesh

        # Base3D draws an object flat unless it says otherwise.
        object_smooth = bool(getattr(obj, 'smooth', False))

        vertices = local * obj.scale.as_numpy
        vertices @= obj.angle
        vertices += obj.position.as_numpy

        self._vertices.append(vertices)

        if object_smooth:
            self._normals.append(self._world_normals(local_normals, obj.scale.as_numpy, obj.angle))
        else:
            self._normals.append(None)

        self._materials.append(obj.material.cl_array)

        return True

    @staticmethod
    @_check_types.do
    def _local_mesh(vbo: "_vbo.VBOHandlerBase | None") -> tuple[np.ndarray, np.ndarray] | None:
        """Return a VBO's local-space triangle soup and its smooth normals, each ``(N, 3)`` float32.

        :param vbo: The VBO handler.
        :type vbo: VBOHandlerBase | None
        :returns: ``(vertices, smooth_normals)``, or ``None`` when there are no whole triangles. A mesh
            that has fewer normals than vertices gets zero vectors for the missing ones.
        :rtype: tuple[numpy.ndarray, numpy.ndarray] | None
        """
        data = getattr(vbo, 'vertices', None)
        if data is None:
            return None

        count = len(data) // 9 * 9
        if not count:
            return None

        vertices = np.array(data[:count], dtype=np.float32).reshape(-1, 3)

        normals = np.zeros((count,), dtype=np.float32)
        smooth = getattr(vbo, 'smooth_normals', None)

        if smooth is not None:
            available = min(count, len(smooth))
            normals[:available] = smooth[:available]

        return vertices, normals.reshape(-1, 3)

    @staticmethod
    @_check_types.do
    def _world_normals(normals: np.ndarray, scale: np.ndarray, angle: "_angle.Angle") -> np.ndarray:
        """Carry local-space normals into world space the way the faces vertex shader does.

        A normal is divided by the scale (not multiplied, as a position is) so that it stays
        perpendicular to a surface that was stretched unevenly, then rotated and made unit
        length again. A zero vector, the mark of a vertex without a normal, stays zero.

        :param normals: ``(N, 3)`` local-space normals.
        :type normals: numpy.ndarray
        :param scale: ``(3,)`` scale applied to the mesh.
        :type scale: numpy.ndarray
        :param angle: Orientation of the placement.
        :type angle: Angle
        :returns: ``(N, 3)`` float32 unit normals (or zero vectors).
        :rtype: numpy.ndarray
        """
        divisor = np.where(scale == 0.0, 1.0, scale).astype(np.float32)

        world = (normals / divisor).astype(np.float32)
        world @= angle

        length = np.linalg.norm(world, axis=1, keepdims=True)
        np.divide(world, length, out=world, where=length > 1e-12)
        return world

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

        # One normal per vertex, zero where an object is flat. Nothing at all when no object is smooth,
        # so a scene of flat parts does not pay for a second vertex-sized buffer.
        vertex_normals = None

        if any(normals is not None for normals in self._normals):
            vertex_normals = np.concatenate([
                np.zeros_like(verts) if normals is None else normals
                for verts, normals in zip(self._vertices, self._normals)])

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
            vertex_normals=vertex_normals,
            bvh_bounds=bvh_bounds,
            bvh_structure=bvh_structure,
            bvh_indices=bvh_indices,
            object_ids=object_ids,
            materials=np.array(self._materials, dtype=np.float32),
            lights=np.array([light.to_array() for light in lights], dtype=np.float32),
            environment_map=self._environment_map()
        )
