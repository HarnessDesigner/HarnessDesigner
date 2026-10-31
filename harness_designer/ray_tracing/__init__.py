# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The offline OpenCL ray tracer.

Nothing is imported here on purpose: :mod:`.renderer` needs ``pyopencl`` and
:mod:`.bvh_processor` needs the compiled ``bvh`` extension, and the application
has to start without either. The dialog that drives the tracer
(:mod:`harness_designer.ui.dialogs.ray_tracing_dialog`) imports
:mod:`.scene`, :mod:`.renderer` and :mod:`.settings` when a render starts.
"""
