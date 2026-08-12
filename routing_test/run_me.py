# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Entry point for the routing/collision benchmark harness.

Step so far: a single window, a locked top-down orthographic camera, the
procedural floor grid, mouse pan/zoom/walk, and now a handful of test
wires rendered through the real faces shader. No collision/routing
logic yet -- that comes in a later step.
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer

from testapp.gl import canvas as _canvas
from testapp.config import Config
from testapp.geometry import point as _point
from testapp.objects import wire as _wire
from testapp.objects import housing as _housing
from testapp.shapes import glyph as _glyph
from testapp import color as _color
from testapp.utils import profiling as _profiling


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Routing / Collision Benchmark Harness")
        self.resize(1280, 800)

        self.canvas = _canvas.Canvas(self, Config)
        self.setCentralWidget(self.canvas)

        # Deferred until after the canvas's first paint (initializeGL) has
        # actually run -- Wire construction needs a live GL context (to
        # build/cache the shared cylinder/helix VBOs), which doesn't exist
        # until then.
        QTimer.singleShot(100, self._build_test_scene)

    def _build_test_scene(self):

        _profiling.reset()

        # Every character this harness will ever need to render, built
        # and cached (real GPU VBOs -- see shapes/glyph.py) once, right
        # here, at startup -- not lazily on first use. Every housing
        # built after this point only ever hits already-uploaded VBOs.
        with self.canvas.context:
            _glyph.build_chars(Config.label.text_depth)

        print(
            '\n--- glyph cache build timing (full keyboard, all 4 styles) ---'
            )
        print(_profiling.report())
        _profiling.reset()

        with self.canvas.context:
            red = _color.Color(220, 50, 50)
            white = _color.Color(255, 255, 255)
            green = _color.Color(50, 180, 60)
            blue = _color.Color(60, 90, 220)

            # Every wire is now a fixed Config.wire.diameter (see
            # objects/wire.py's own docstring) -- no more per-wire
            # diameter argument to vary here.
            wires = [
                _wire.Wire(_point.Point(-10.0, 0.0, -20.0), _point.Point(10.0, 0.0, -20.0),
                          red, stripe_color=white),
                _wire.Wire(_point.Point(-10.0, 0.0, -10.0), _point.Point(10.0, 0.0, -10.0),
                          green),
                _wire.Wire(_point.Point(-10.0, 0.0, 0.0), _point.Point(10.0, 0.0, 0.0),
                          blue),

                _wire.Wire(_point.Point(-10.0, 0.0, 10.0), _point.Point(10.0, 0.0, 10.0),
                          red, stripe_color=white),
                _wire.Wire(_point.Point(-10.0, 0.0, 20.0), _point.Point(10.0, 0.0, 20.0),
                          green),
                _wire.Wire(_point.Point(-10.0, 0.0, 30.0), _point.Point(10.0, 0.0, 30.0),
                          blue),
            ]

        for w in wires:
            self.canvas.add_object(w)

        with self.canvas.context:
            # Matches the mock-up: 16 cavities, ascending order, a
            # handful seated with a terminal (the rest just show a bare
            # cavity number with no bracket/wire-stub).
            seated = {1, 2, 4, 5, 6, 10, 16}
            cavities = [
                {'name': str(i), 'terminal_name': f'Terminal {i}' if i in seated else None}
                for i in range(1, 17)
            ]
            housing = _housing.Housing(_point.Point(30.0, 0.0, 0.0), 0.0, cavities)

        self.canvas.add_object(housing)

        # Should be near-empty now -- every glyph this housing needs was
        # already built above, so building it is just cheap lookups
        # (see shapes/glyph.py's get()) plus per-character Point/VBO
        # bookkeeping, no build123d/OCCT calls at all.
        print('\n--- housing build timing (one 16-cavity housing) ---')
        print(_profiling.report())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
