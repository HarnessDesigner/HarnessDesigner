# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Schema for the ``wire_conductors`` table.

One row per individual conductor inside a multi-conductor wire. The ``wires`` table describes the OUTSIDE of such a
wire (its jacket colour, overall size, shielding, ``tpi`` ...); this table describes each conductor INSIDE it. This is
global catalog data, static for each wire, not a per-project table.

Nothing here is unique except the row id. ``wire_id`` is the row id of the cable in ``wires`` and ``idx`` is the
conductor's position within the cable (the first conductor is ``0``). The rest are the things that can differ from
conductor to conductor: ``color_id`` and ``stripe_color_id`` (both the "no color" row,
``id_generator.NO_COLOR_UUID``, when there is no stripe), ``core_material_id`` (the plating of the metal),
``material_id`` (the insulation), the size columns, ``strands``, ``od_mm`` (over the conductor's own insulation)
and ``resistance_1km``.

A cable has an outer jacket when its ``wires.color_id`` is not the "no color" row; a cable without one is drawn as
its twisted conductors (see ``TWISTED_WIRE_DESIGN.md`` in the repo root).

NEW 2026-11-03. Mirrored in the sibling ``harness_designer_database`` repo
(``builder/create_database/wire_conductors.py``), which builds the shared catalog; keep the two aligned.
"""

from typing import TYPE_CHECKING

from . import colors as _colors
from . import materials as _materials
from . import platings as _platings
from . import wires as _wires
from .. import db_connectors as _con
from .. import id_generator as _id_generator
from ... import logger as _logger


if TYPE_CHECKING:
    from ..global_db import bases as _glb_bases


_NO_COLOR_DEFAULT = f"X'{_id_generator.NO_COLOR_UUID.hex}'"

id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'wire_conductors',
    id_field,
    _con.UUIDField('wire_id', no_null=True,
                   references=_con.SQLFieldReference(_wires.table,
                                                     _wires.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    _con.UUIDField('color_id', default=_NO_COLOR_DEFAULT, no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stripe_color_id', default=_NO_COLOR_DEFAULT, no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('core_material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_platings.table,
                                                     _platings.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_materials.table,
                                                     _materials.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.FloatField('wire_size_dia', default='NULL'),
    _con.FloatField('wire_size_cross', default='NULL'),
    _con.IntField('wire_size_awg', default='NULL'),
    _con.IntField('strands', default='1'),
    _con.FloatField('od_mm', default='"0.0"', no_null=True),
    _con.FloatField('resistance_1km', default='"0.0"', no_null=True)
)


def add_indexes(db_cursor: "_glb_bases.TableBase") -> None:
    """
    Index ``wire_id``, so a cable's conductors are found without reading every row of the catalog's.

    Only SQLite needs it: a MySQL foreign key already indexes its column. ``IF NOT EXISTS`` makes it safe to run on
    every start, and it is skipped quietly where the database cannot be written to (the lookup is then a scan, which
    is slower but not wrong).

    :param db_cursor: The ``wire_conductors`` table class.
    :type db_cursor: :class:`_glb_bases.TableBase`
    """

    if _con.Config.database.connector != _con.CONNECTOR_SQLITE:
        return

    try:
        db_cursor._con.execute(
            'CREATE INDEX IF NOT EXISTS wire_conductors_wire_id_index ON wire_conductors (wire_id);')

        db_cursor._con.commit()
    except Exception as exc:  # NOQA
        _logger.database(f'could not index the wire_conductors table: {exc!r}')
