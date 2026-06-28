# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import wire_conversions as _wc
from . import remap as _remap
from . import ui_utils as _uu
from . import snap_pool as _snap_pool
from . import paths as _paths
from . import mesh_normals as _mn
from . import bounding_boxes as _bb
from . import model_utils as _mu


mm2_to_awg = _wc.mm2_to_awg
awg_to_mm2 = _wc.awg_to_mm2
awg_to_d_in = _wc.awg_to_d_in
awg_to_d_mm = _wc.awg_to_d_mm
d_in_to_d_mm = _wc.d_in_to_d_mm
d_mm_to_mm2 = _wc.d_mm_to_mm2
mm2_to_d_mm = _wc.mm2_to_d_mm
mm2_to_d_in = _wc.mm2_to_d_in
d_mm_to_awg = _wc.d_mm_to_awg
mm2_to_in2 = _wc.mm2_to_in2
in2_to_mm2 = _wc.in2_to_mm2

remap = _remap.remap

HSizer = _uu.HSizer
IMAGE_FILE_WILDCARDS = _uu.IMAGE_FILE_WILDCARDS
MODEL_FILE_WILDCARDS = _uu.MODEL_FILE_WILDCARDS

SnapPool = _snap_pool.SnapPool

get_appdata = _paths.get_appdata
get_documents = _paths.get_documents

compute_smooth_normals = _mn.compute_smooth_normals
compute_face_normals = _mn.compute_face_normals
compute_normals = _mn.compute_normals
compute_face_indexes = _mn.compute_face_indexes


adjust_aabb = _bb.adjust_aabb
compute_aabb = _bb.compute_aabb
compute_obb = _bb.compute_obb

compute_edges = _mu.compute_edges
convert_model_to_mesh = _mu.convert_model_to_mesh


del _wc
del _remap
del _uu
del _snap_pool
del _paths
del _mn
del _bb
del _mu
