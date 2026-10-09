# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""AMD GPU metrics backend for :mod:`harness_designer.gpu`, via
``pyamd_adl`` (replaces the previous ``amdsmi``-based implementation).

Coverage here is necessarily partial and best-effort, not verified against
real AMD hardware (this development machine has none) -- ADL's own surface
is more control-oriented (OverDrive tuning) than a clean read-only sensor
API, and its shape has shifted across OverDrive versions 5/6/7/8 (see
``pyamd_adl``'s own ``adapter_h.py`` -- ``Adapter.core``/``.memory`` already
abstract that version dispatch internally). If a field below turns out
wrong or missing once run against real hardware, fix it there -- every
access is wrapped individually so one wrong field degrades to ``None``
rather than breaking collection of everything else.
"""

from ..backend_base import GPUBackend, DisplayPortInfo
from ... import check_types as _check_types


class AMDBackend(GPUBackend):
    """Collects metrics from the first AMD GPU via :mod:`pyamd_adl`.

    Every metric is queried once at construction time. ADL initialization
    itself raises outright with no AMD adapter/driver present -- that,
    like every individual metric below, leaves this backend at
    :class:`.backend_base.GPUBackend`'s all-``None`` default rather than
    propagating.
    """

    @_check_types.do
    def __init__(self) -> None:
        import pyamd_adl

        adapter = None
        try:
            for found in pyamd_adl.adapters:
                adapter = found
                break
        except Exception:  # NOQA -- no AMD adapter/driver on this system
            return

        if adapter is None:
            return

        self.gpu_manufacturer = 'AMD'

        try:
            self.gpu_name = adapter.name
        except Exception:  # NOQA
            pass

        memory = adapter.memory

        try:
            size = memory.size
            if size is not None:
                self.vram_size = size * 1024 * 1024  # ADL reports MB
        except Exception:  # NOQA
            pass

        try:
            # ADL has no separate "model" string distinct from memory type
            # (e.g. "GDDR6") -- not a true equivalent of nvapi's chip/board
            # identifier, just the closest thing ADL exposes.
            self.gpu_model = memory.type
        except Exception:  # NOQA
            pass

        try:
            self.pcie_bandwidth = memory.bandwidth
        except Exception:  # NOQA
            pass

        try:
            # Dedicated-only usage is the closer analogue to nvapi's
            # dedicated_memory/current_available_dedicated_memory scope;
            # vram_usage (total incl. shared) is the fallback.
            usage_mb = adapter.dedicated_vram_usage
            if usage_mb is None:
                usage_mb = adapter.vram_usage
            if usage_mb is not None:
                self.vram_use = usage_mb * 1024 * 1024
        except Exception:  # NOQA
            pass

        try:
            self.gpu_cores = adapter.gcn_info.compute_units
        except Exception:  # NOQA
            pass

        try:
            # One call gives base/game/boost/memory clocks together --
            # prefer the "game" (real-world sustained) clock for soc_clock
            # over the older Core.clock (which reads more like an
            # instantaneous observed value with less consistent meaning
            # across ADL versions).
            clocks = adapter.game_clock_info
            self.soc_clock = clocks.game
            self.memory_clock = clocks.memory
        except Exception:  # NOQA
            try:
                self.soc_clock = adapter.core.clock
            except Exception:  # NOQA
                pass

            try:
                self.memory_clock = memory.observed_clock
            except Exception:  # NOQA
                pass

        try:
            load = adapter.core.load
            self.gpu_engine = float(load) if load is not None else None
        except Exception:  # NOQA
            pass

        try:
            temps = adapter.temperatures
            if temps:
                # Temperature subclasses float directly (see
                # pyamd_adl.overdrive8_h.FloatValueWrapper) -- usable as a
                # plain number with no further unwrapping.
                self.gpu_temp = float(temps[0])
        except Exception:  # NOQA
            pass

        try:
            fans = adapter.fan_speeds
            if fans:
                self.fan_speed = float(fans[0])
        except Exception:  # NOQA
            pass

        self.displays = []
        try:
            from pyamd_adl.adapter_h import DisplayConnection

            display_conn = DisplayConnection(adapter.index, 0)

            for connector in display_conn.ports:
                info = DisplayPortInfo()

                try:
                    info.index = connector.index
                except Exception:  # NOQA
                    pass

                try:
                    # Raw ADL_DISPLAY_CONTYPE_* int -- pyamd_adl has no
                    # string label for this either (AdapterConnector.label
                    # is the same str(int)), so this matches the existing
                    # library's own convention rather than falling short of it.
                    info.connector_type = connector.type
                except Exception:  # NOQA
                    pass

                try:
                    info.is_connected = connector.is_connected
                except Exception:  # NOQA
                    pass

                try:
                    display = connector.display
                except Exception:  # NOQA
                    display = None

                if display is not None:
                    try:
                        info.monitor_name = display.name
                    except Exception:  # NOQA
                        pass

                    try:
                        info.edid_data = display.edid_data
                    except Exception:  # NOQA
                        pass

                # ADL has no clean per-port "is this mode currently active"
                # equivalent to nvapi's Port.is_active, and no verified way
                # to read the currently-active resolution/refresh (see this
                # module's own docstring) -- both stay None, not a guess.

                self.displays.append(info)
        except Exception:  # NOQA
            pass
