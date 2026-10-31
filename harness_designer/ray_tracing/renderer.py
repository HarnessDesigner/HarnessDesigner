# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""OpenCL-backed rendering helpers for the ray-tracing pipeline."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Union as _Union

import os
import threading
import warnings

import numpy as np
import pyopencl as cl

from .. import gpu as _gpu
from .. import logger as _logger
from .. import check_types as _check_types


if TYPE_CHECKING:
    from . import scene as _scene


# Suppress OpenCL compiler warnings
warnings.filterwarnings('ignore', category=cl.CompilerWarning)

KERNEL_PATH = os.path.join(os.path.dirname(__file__), 'kernel.cl')

# Largest single launch, in pixels. Free memory is not the only reason to split a render: one launch
# over a huge image reports no progress until it ends, and a display GPU that stays busy for a couple
# of seconds gets reset by the OS (Windows TDR). So a render is always split at least this finely.
MAX_PIXELS_PER_CHUNK = 1_000_000

# Share of the GPU's free memory a render plans to use, scene buffers included; the display and
# other programs need the rest.
MEMORY_FRACTION = 0.8

# The kernel writes RGB float32 for every pixel.
BYTES_PER_PIXEL = 3 * 4

GIB = 1024 ** 3

# Floats in the kernel's ``floor_params`` (see ``RenderSettings.floor_params``).
FLOOR_PARAMS = 24


class Renderer:

    """Compile the OpenCL kernel and execute chunked ray-tracing work for a prepared :class:`Scene`.

    The render runs on a worker thread. The callbacks are called from that
    thread, so a GUI has to hand them over to its own thread (a Qt signal does).
    """
    @_check_types.do
    def __init__(self, scene: "_scene.Scene", on_chunk: Callable[[int, np.ndarray, float], None],
                 on_finished: Callable[[bool], None], on_error: Callable[[Exception], None]):
        """Pick the OpenCL device and size the render chunks.

        :param scene: Scene to render; its :meth:`~.scene.Scene.build` is
            called on the worker thread.
        :type scene: Scene
        :param on_chunk: ``on_chunk(start_y, rgb, progress)`` -- called with each
            finished band of rows as a ``(rows, width, 3)`` uint8 array, and the
            percent complete.
        :type on_chunk: callable
        :param on_finished: ``on_finished(cancelled)`` -- called once the render
            ends without an error.
        :type on_finished: callable
        :param on_error: ``on_error(exception)`` -- called if the render fails.
        :type on_error: callable
        """
        self.scene = scene
        self.on_chunk = on_chunk
        self.on_finished = on_finished
        self.on_error = on_error

        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

        self.device: "cl.Device | None" = None
        self.gpu: _Union[_gpu.GPU, None] = None

        self.ctx, self.queue = self.init_cl()

    @_check_types.do
    def init_cl(self) -> tuple["cl.Context", "cl.CommandQueue"]:  # NOQA
        """Initialize the OpenCL platform and command queue, and ask the driver about the device's memory.

        Prefers a GPU device and falls back to a CPU device. Sets :attr:`device` and :attr:`gpu`.

        :returns: A tuple containing the OpenCL context and command queue.
        :rtype: tuple
        :raises RuntimeError: When no OpenCL device is available.
        """
        device = None

        for device_type in (cl.device_type.GPU, cl.device_type.CPU):
            for platform in cl.get_platforms():
                try:
                    devices = platform.get_devices(device_type=device_type)
                except cl.Error:
                    continue

                if devices:
                    device = devices[0]
                    break

            if device is not None:
                break

        if device is None:
            raise RuntimeError('No OpenCL devices found')

        ctx = cl.Context([device])
        queue = cl.CommandQueue(ctx)

        self.device = device
        self.gpu = self._detect_gpu(device)

        return ctx, queue

    @_check_types.do
    def _detect_gpu(self, device: "cl.Device") -> _Union[_gpu.GPU, None]:
        """Read the GPU's memory from the display driver.

        :meth:`.gpu.GPU.detect` finds the vendor from ``glGetString``, which only
        answers on a thread that has an OpenGL context current, and without a
        vendor it falls back to a made-up 4 GiB / 2 GiB. So a throwaway context
        is made current here (the same way ``gl.info`` does) for the call. Must
        run on the GUI thread.

        :param device: The OpenCL device the render will use.
        :type device: pyopencl.Device
        :returns: The detected GPU, or ``None`` for a CPU device or when the driver could not be queried.
        :rtype: GPU | None
        """
        if not device.type & cl.device_type.GPU:
            return None

        from PySide6 import QtGui
        from ..gpu import gpu_vendor as _gpu_vendor

        fmt = QtGui.QSurfaceFormat.defaultFormat()

        surface = QtGui.QOffscreenSurface()
        surface.setFormat(fmt)
        surface.create()

        context = QtGui.QOpenGLContext()
        context.setFormat(fmt)

        try:
            if not (context.create() and context.makeCurrent(surface)):
                _logger.warning('RENDERER: no OpenGL context for GPU detection; using OpenCL memory figures')
                return None

            try:
                if _gpu_vendor.get() == _gpu_vendor.GPU_UNKNOWN:
                    _logger.warning('RENDERER: GPU vendor not recognised; using OpenCL memory figures')
                    return None

                gpu = _gpu.GPU(device)
                gpu.detect()
                return gpu
            finally:
                context.doneCurrent()
        except Exception as err:  # NOQA
            _logger.warning(f'RENDERER: GPU detection failed ({err}); using OpenCL memory figures')
            return None
        finally:
            surface.destroy()

    @_check_types.do
    def _free_memory(self) -> int:
        """Bytes of device memory a render can count on.

        Free memory is total minus used as the display driver reports them
        (:meth:`_detect_gpu`). Without driver figures it is half of what OpenCL
        says the device has.

        :rtype: int
        """
        total = int(self.device.global_mem_size)
        free = None

        gpu = self.gpu
        if gpu is not None:
            size, used = gpu.vram_size.value, gpu.vram_use.value

            if isinstance(size, (int, float)) and isinstance(used, (int, float)) and size > 0:
                free = int(size - used)
                _logger.info(f'RENDERER: driver reports {size / GIB:.2f} GiB total, {used / GIB:.2f} GiB used')

        if free is None or free <= 0:
            free = total // 2
            _logger.warning(f'RENDERER: no driver memory figures; assuming {free / GIB:.2f} GiB free')

        return min(free, total)

    @_check_types.do
    def _chunk_rows(self, width: int, height: int, scene_bytes: int) -> int:
        """Choose how many rows to render per launch.

        The smallest of: what fits in the free memory left after the scene's
        buffers, what one OpenCL buffer may hold (``max_mem_alloc_size``, often
        a quarter of the device), and :data:`MAX_PIXELS_PER_CHUNK`.

        :param width: Image width in pixels.
        :type width: int
        :param height: Image height in pixels.
        :type height: int
        :param scene_bytes: Device memory the scene's buffers already take.
        :type scene_bytes: int
        :returns: Rows per launch, at least 1 and at most ``height``.
        :rtype: int
        """
        free = self._free_memory()
        row_bytes = width * BYTES_PER_PIXEL

        by_memory = (int(free * MEMORY_FRACTION) - scene_bytes) // row_bytes
        by_buffer = int(self.device.max_mem_alloc_size) // row_bytes
        by_pixels = MAX_PIXELS_PER_CHUNK // width

        rows = max(1, min(height, by_memory, by_buffer, by_pixels))
        chunks = (height + rows - 1) // rows

        _logger.info(f'RENDERER: chunk strategy for {width}x{height}:')
        _logger.info(f'RENDERER:   free {free / GIB:.2f} GiB, scene {scene_bytes / GIB:.3f} GiB')
        _logger.info(f'RENDERER:   rows that fit: memory {by_memory}, one buffer {by_buffer}, '
                     f'pixel cap {by_pixels}')
        _logger.info(f'RENDERER:   {rows} rows per chunk, {chunks} chunks, '
                     f'{rows * row_bytes / GIB:.3f} GiB per chunk')

        return rows

    @_check_types.do
    def compile_kernel(self) -> "cl.Kernel":
        """Load and compile the OpenCL kernel used for ray tracing.

        :returns: The ``ray_trace_kernel`` kernel.
        :rtype: cl.Kernel
        """
        with open(KERNEL_PATH, 'r', encoding='utf-8') as f:
            kernel_source = f.read()

        program = cl.Program(self.ctx, kernel_source).build()
        return cl.Kernel(program, 'ray_trace_kernel')

    @_check_types.do
    def start(self) -> None:
        """Start rendering on a worker thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @_check_types.do
    def cancel(self) -> None:
        """Ask the render to stop; it stops after the chunk it is working on."""
        self._cancel.set()

    @_check_types.do
    def _run(self) -> None:
        """Worker thread body: render, then report how it ended."""
        try:
            self._render()
        except Exception as err:  # NOQA
            self.on_error(err)
        else:
            self.on_finished(self._cancel.is_set())

    @_check_types.do
    def _render(self) -> None:
        """Build the scene, upload it, and render it one band of rows at a time."""
        scene = self.scene
        data = scene.build()
        settings = scene.settings

        kernel = self.compile_kernel()

        mf = cl.mem_flags
        buffers = []
        scene_bytes = 0

        def upload(array: np.ndarray) -> "cl.Buffer":
            nonlocal scene_bytes

            array = np.ascontiguousarray(array)
            buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=array)
            buffers.append(buf)
            scene_bytes += array.nbytes
            return buf

        try:
            vertices_buf = upload(data.vertices)
            faces_buf = upload(data.faces)
            object_ids_buf = upload(data.object_ids)
            materials_buf = upload(data.materials)
            lights_buf = upload(data.lights)
            floor_buf = upload(np.array(
                settings.floor_params if settings.floor_enabled else (0.0,) * FLOOR_PARAMS,
                dtype=np.float32))
            bvh_bounds_buf = upload(data.bvh_bounds)
            bvh_structure_buf = upload(data.bvh_structure)
            bvh_indices_buf = upload(data.bvh_indices)

            if data.environment_map is not None:
                env_height, env_width = data.environment_map.shape[:2]
                env_buf = upload(data.environment_map)
            else:
                env_width = env_height = 1
                env_buf = upload(np.zeros((1, 1, 3), dtype=np.uint8))

            forward = scene.camera_target - scene.camera_origin
            forward /= np.linalg.norm(forward)
            right = np.cross(forward, scene.camera_up)
            right /= np.linalg.norm(right)
            up = np.cross(right, forward)

            width = scene.width
            height = scene.height
            aspect_ratio = width / height
            scale = np.tan(np.radians(scene.fov) / 2)

            chunk_size = self._chunk_rows(width, height, scene_bytes)
            num_chunks = (height + chunk_size - 1) // chunk_size

            chunk_image = np.empty((chunk_size, width, 3), dtype=np.float32)
            chunk_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY, chunk_image.nbytes)
            buffers.append(chunk_buf)

            for chunk_idx in range(num_chunks):
                if self._cancel.is_set():
                    return

                start_y = chunk_idx * chunk_size
                end_y = min(start_y + chunk_size, height)
                chunk_height = end_y - start_y

                kernel.set_args(
                    vertices_buf,
                    faces_buf,
                    object_ids_buf,
                    materials_buf,
                    np.int32(len(data.faces)),
                    lights_buf,
                    np.int32(len(data.lights)),
                    bvh_bounds_buf,
                    bvh_structure_buf,
                    bvh_indices_buf,
                    chunk_buf,
                    np.int32(width),
                    np.int32(height),
                    *(np.float32(item) for item in scene.camera_origin),
                    *(np.float32(item) for item in scene.camera_target),
                    *(np.float32(item) for item in right),
                    *(np.float32(item) for item in up),
                    *(np.float32(item) for item in forward),
                    np.float32(scale),
                    np.float32(aspect_ratio),
                    np.int32(start_y),
                    np.int32(end_y),
                    np.float32(settings.ambient_intensity),
                    *(np.float32(item) for item in settings.background_color1),
                    *(np.float32(item) for item in settings.background_color2),
                    env_buf,
                    np.int32(env_width),
                    np.int32(env_height),
                    np.int32(settings.enable_gradient),
                    np.int32(data.environment_map is not None),
                    np.int32(settings.enable_reflections),
                    np.int32(settings.enable_shadows),
                    np.int32(settings.enable_ambient_occlusion),
                    np.int32(settings.enable_depth_of_field),
                    np.float32(settings.ambient_occlusion_samples),
                    np.float32(settings.ambient_occlusion_radius),
                    np.float32(settings.shadow_softness),
                    floor_buf,
                    np.uint32(settings.floor_stipple_pattern),
                    np.int32(settings.floor_stipple_phase)
                )

                cl.enqueue_nd_range_kernel(self.queue, kernel, (width, chunk_height), None)
                cl.enqueue_copy(self.queue, chunk_image, chunk_buf).wait()

                rgb = (chunk_image[:chunk_height] * 255).astype(np.uint8)
                self.on_chunk(start_y, rgb, (chunk_idx + 1) / num_chunks * 100)
        finally:
            for buf in buffers:
                buf.release()
