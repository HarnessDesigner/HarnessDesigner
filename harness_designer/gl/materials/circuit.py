# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import glowing as _glowing
from ... import color as _color
from ... import check_types as _check_types


class CircuitMaterial(_glowing.GlowingMaterial):
    """The material every member of a selected circuit is shown with.

    ``objects.circuit.Circuit.highlight`` hands one of these to ``identify()`` on each wire, service loop, splice and terminal of the
    circuit (a material override, NOT a selection: the canvas only ever has the circuit itself selected), and ``identify(None)`` puts
    them back when the circuit is deselected. It is an emissive :class:`GlowingMaterial`, so every member reads as the same colour
    whatever its own colour is. The colour is :attr:`COLOR` for now; making it user-tunable means adding it to ``Config.colors``.
    """
    # amber (r, g, b, a)
    COLOR = (255, 170, 0, 255)

    @_check_types.do
    def __init__(self, color: _color.Color | None = None):
        """Initialise the :class:`CircuitMaterial` instance.

        :param color: The glow's colour, or ``None`` for :attr:`COLOR`.
        :type color: :class:`_color.Color` | None
        """
        if color is None:
            color = _color.Color(*self.COLOR)

        super().__init__(color)
