# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""3D-editor rotation gizmo -- see :mod:`.generic` (``Rings3D``, built
around the ``rotation_ring`` submodule's torus + protractor rings) for
the one implementation every rotatable 3D object type currently shares.
No per-object-type override exists yet -- kept as a generic.py-first
module here, mirroring :mod:`~harness_designer.drag_handlers.editor_3d`'s
own generic/specific split, so a future object type needing bespoke
rotation behavior has a place to live without restructuring this
package again.
"""
