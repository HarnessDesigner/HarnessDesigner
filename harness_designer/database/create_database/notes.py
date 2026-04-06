
from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from harness_designer.database import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_notes',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', default='NULL',
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', default='NULL',
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('size2d', no_null=True),
    _con.IntField('h_align2d', no_null=True),
    _con.IntField('v_align2d', no_null=True),
    _con.IntField('style2d', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('size3d', no_null=True),
    _con.IntField('h_align3d', no_null=True),
    _con.IntField('v_align3d', no_null=True),
    _con.IntField('style3d', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
