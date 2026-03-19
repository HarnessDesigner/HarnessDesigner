
from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import numpy as np
import ctypes
import threading

from ...geometry.decimal import Decimal as _d


if TYPE_CHECKING:
    from . import canvas as _canvas


class Grid:

    def __init__(self, canvas: "_canvas.Canvas2D"):
        self.canvas = canvas

        self.vbos = None
        self.thread = None

        self.config = canvas.config

    def _initialize_grid(self):
        """
        Compute the "Floor" and store it in the graphics adapter memory.

        This allows for a super fast render of the floor.

        :return:
        """

        size = _d(self.config.grid.size) / _d(2.0)
        num_layers = min(7, int(size / _d(1000)))

        def _get_vbo(verts):
            # Flatten the data
            verts = np.array(verts, dtype=np.float32).flatten()

            # Calculate the number of vertices (for rendering)
            verts_count = len(verts)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, verts.nbytes,
                            verts, GL.GL_STATIC_DRAW)

            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)  # Unbind the VBO

            return vbo, int(verts_count)

        layer_factors = [_d(10.0)]

        for _ in range(num_layers - 1):
            layer_factors.append(layer_factors[-1] * _d(2.0))

        layer_steps = [size / item for item in layer_factors]
        layers = [[] for _ in range(num_layers)]

        def _frange(start, stop, step):
            cur = start
            while cur < stop:
                yield cur

                cur += step

        for y in _frange(_d(0.0), size + layer_steps[-1], layer_steps[-1]):
            for x in _frange(_d(0.0), size + layer_steps[-1], layer_steps[-1]):

                for i, layer_step in enumerate(layer_steps):
                    if not x % layer_step and not y % layer_step:
                        layers[i].extend([[float(x), float(y)], [-float(x), float(y)],
                                          [float(x), -float(y)], [-float(x), -float(y)]])

        event = threading.Event()

        def _do():
            self.vbos = [_get_vbo(layer) for layer in layers]
            self.canvas.Refresh(False)
            event.set()

        wx.CallAfter(_do)

        event.wait()

    def set(self, flag):
        def _do(f):
            with self.canvas.context:
                if self.vbos is not None:
                    for vbo, _ in self.vbos:

                        try:
                            GL.glDeleteBuffers(1, [vbo])
                        except:  # NOQA
                            pass

                    self.vbos = None

                if self.thread is None and f:
                    self.thread = threading.Thread(target=self._initialize_grid)
                    self.thread.daemon = True
                    self.thread.start()

        wx.CallAfter(_do, flag)

    def render(self, zoom):
        """Render the precomputed grid using the VBO."""

        if self.vbos is None:
            return

        # type_ is either GL.GL_LINES or GL.GL_QUADS
        def _draw_vbo(vbo, count):
            # Setup the VBO for rendering
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

            stride = 0  # No stride between consecutive vertex positions
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            # First 3 floats are position
            GL.glVertexPointer(2, GL.GL_FLOAT, stride, ctypes.c_void_p(0))

            # Draw
            GL.glDrawArrays(GL.GL_POINTS, 0, count)

            # Cleanup
            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)

        num_layers = len(self.vbos)
        zoom_levels = [100]
        for _ in range(num_layers - 1):
            zoom_levels.append(zoom_levels[-1] * 2.5)

        for i, level in enumerate(zoom_levels):
            i = ~i + num_layers
            if zoom <= level:
                major = i
                break
        else:
            major = 0

        if major < num_layers - 1:
            GL.glColor4f(0.75, 0.75, 0.75, 1.0)  # Light gray
            GL.glPointSize(1.75)
            _draw_vbo(*self.vbos[major + 1])

        GL.glColor4f(0.25, 0.25, 0.25, 1.0)  # Dark gray for contrast
        GL.glPointSize(2.5)
        _draw_vbo(*self.vbos[major])
