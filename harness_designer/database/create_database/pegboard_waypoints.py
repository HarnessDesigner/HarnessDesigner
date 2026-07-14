# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_pegboard_waypoints``.

Bend points that exist only in the peg-board view -- they have no 3D
counterpart. Each row belongs to a bundle chain and is ordered along it by
``sequence``. ``max_length_before_mm`` is the fixed length budget of the
edge ending at that waypoint.
"""

from . import projects as _projects
from . import bundle_covers as _bundle_covers

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_pegboard_waypoints',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('bundle_id', no_null=True,
                  references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                    _bundle_covers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('sequence', no_null=True),
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    _con.FloatField('max_length_before_mm', no_null=True)
)
