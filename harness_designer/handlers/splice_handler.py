# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Compatibility-check helper for inserting splices into wires, reused
by ``objects.objects_3d.splice.Splice.start_add``/``objects.objects_
schematic.splice.Splice.start_add`` (see ``add_handlers.editor_3d.
splice``/``add_handlers.editor_schematic.splice`` for the actual
interactive placement sessions, which replaced this module's own
former ``AddSpliceHandler``).
"""

from .. import check_types as _check_types


@_check_types.do
def _wire_fits(splice_part, wire) -> bool:
    """
    Return True when the wire's AWG falls within the splice's accepted range.
    """
    part = wire.db_obj.part
    if part is None:
        return False

    wire_awg = part.size_awg
    if wire_awg is None:
        return False

    awg_min = splice_part.wire_size_awg_min
    awg_max = splice_part.wire_size_awg_max
    # AWG is inverse: higher number = smaller wire. awg_min is derived from
    # the splice's MINIMUM (thinnest) accepted wire diameter -- see
    # database.global_db.mixins.wire_size.WireSizeMixin's wire_size_dia_min
    # setter, which always derives _awg_min from dia_min via d_mm_to_awg --
    # so it is numerically the LARGER awg number (smallest wire); awg_max
    # (from the thickest accepted diameter) is numerically the smaller one
    # (largest wire).
    if awg_min is not None and wire_awg > awg_min:
        return False

    if awg_max is not None and wire_awg < awg_max:
        return False

    return True
