# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Common vendor-backend interface for :mod:`harness_designer.gpu`.

Every concrete backend (:class:`.nvidia.NvidiaBackend`, :class:`.amd.AMDBackend`,
...) exposes this same set of plain attribute names -- one per
:class:`.gpu.GPU` attribute -- so :class:`.gpu.GPU` never needs
vendor-specific branching to collect metrics, only to pick which backend
class to instantiate (see ``GPU.detect()``).

A backend queries everything it can once, at construction time, and leaves
whatever its vendor API doesn't expose (or fails/isn't supported on the
current driver/hardware -- a normal outcome, not an error) at this base
class's default of ``None``. :class:`.gpu.GPU`'s generic collection step
copies every non-``None`` attribute across; a ``None`` just leaves that
:class:`.gpu_base.GPUAttribute` at its own default ``'Unknown'`` display
value.

No vendor is expected to populate every attribute here -- ADL (AMD) in
particular exposes a materially different, more control-oriented surface
than NVML/NVAPI, so AMD's coverage is necessarily partial. Partial, honest
coverage beats a wrong guess at a field that doesn't really mean what it's
being mapped to.
"""


class DisplayPortInfo:
    """One physical display connector and whatever is plugged into it.

    Every field defaults to ``None``/``False`` (not collected) same as
    :class:`GPUBackend` itself -- a vendor populates whatever it can.
    """

    index = None
    connector_type = None
    is_connected = None
    is_active = None
    monitor_name = None
    edid_data = None
    # (width, height, refresh_hz) of the currently active mode, or None.
    resolution = None


class GPUBackend:
    """Base class: every metric defaults to ``None`` (not collected)."""

    # One DisplayPortInfo per physical connector on the GPU. Always a list
    # (empty if nothing was collected), never None.
    displays: list = ()

    # Mirrors harness_designer.gpu.gpu.GPU's own attribute names one-to-one.
    ATTRIBUTE_NAMES = (
        'driver_name', 'driver_version', 'driver_date',
        'gpu_model', 'gpu_name', 'gpu_manufacturer', 'gpu_serial', 'gpu_cores',
        'architecture', 'generation', 'foundry',
        'vram_size', 'vram_width', 'vram_use', 'memory_type', 'memory_bandwidth',
        'gpu_engine', 'memory_engine',
        'soc_clock', 'boost_clock', 'memory_clock',
        'pcie_max_width', 'pcie_width', 'pcie_max_speed', 'pcie_speed',
        'pcie_bandwidth', 'pcie_version',
        'fan_speed_rpm', 'fan_speed',
        'gpu_temp',
    )

    driver_name = None
    driver_version = None
    driver_date = None

    gpu_model = None
    gpu_name = None
    gpu_manufacturer = None
    gpu_serial = None
    gpu_cores = None

    # Static, model-level identity -- not runtime-queryable on any vendor
    # here, only ever filled in from a :mod:`.vram_lookup`-based spec table
    # (see e.g. :mod:`.amd_vram_table`) matched against GL_RENDERER/model name.
    architecture = None
    generation = None
    foundry = None

    vram_size = None
    vram_width = None
    vram_use = None
    memory_type = None
    memory_bandwidth = None

    gpu_engine = None
    memory_engine = None

    # soc_clock is the "current/observed" reading where a backend has one;
    # boost_clock is the model's rated maximum, distinct from it, and (like
    # architecture/generation/foundry above) only ever comes from a static
    # spec table, not a live query.
    soc_clock = None
    boost_clock = None
    memory_clock = None

    pcie_max_width = None
    pcie_width = None
    pcie_max_speed = None
    pcie_speed = None
    pcie_bandwidth = None
    pcie_version = None

    fan_speed_rpm = None
    fan_speed = None

    gpu_temp = None
