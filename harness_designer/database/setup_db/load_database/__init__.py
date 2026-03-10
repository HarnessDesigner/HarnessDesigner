from . import accessories as _accessories
from . import adhesives as _adhesives
from . import boots as _boots
from . import bundle_covers as _bundle_covers
from . import cavities as _cavities
from . import cavity_locks as _cavity_locks
from . import colors as _colors
from . import covers as _covers
from . import cpa_lock_types as _cpa_lock_types
from . import cpa_locks as _cpa_locks
from . import directions as _directions
from . import families as _families
from . import file_types as _file_types
from . import genders as _genders
from . import housings as _housings
from . import ip_fluids as _ip_fluids
from . import ip_ratings as _ip_ratings
from . import ip_solids as _ip_solids
from . import ip_supps as _ip_supps
from . import manufacturers as _manufacturers
from . import materials as _materials
from . import model3d as _model3d
from . import platings as _platings
from . import protections as _protections
from . import resources as _resources
from . import seal_types as _seal_types
from . import seals as _seals
from . import series as _series
from . import settings as _settings
from . import shapes as _shapes
from . import splice_types as _splice_types
from . import splices as _splices
from . import temperatures as _temperatures
from . import terminals as _terminals
from . import tpa_locks as _tpa_locks
from . import transition_branches as _transition_branches
from . import transition_series as _transition_series
from . import transitions as _transitions
from . import wire_markers as _wire_markers
from . import wires as _wires


def create_tables(con, cur):
    modules = (
        _adhesives,
        _cavities,
        _colors,
        _cpa_lock_types,
        _directions,
        _file_types,
        _genders,
        _ip_fluids,
        _ip_solids,
        _ip_supps,
        _materials,
        _platings,
        _protections,
        _resources,
        _seal_types,
        _settings,
        _shapes,
        _splice_types,
        _temperatures,
        _transition_series,
        _families,
        _series,
        _accessories,
        _boots,
        _bundle_covers,
        _covers,
        _cpa_locks,
        _housings,
        _seals,
        _splices,
        _terminals,
        _tpa_locks,
        _transitions,
        _transition_branches,
        _wire_markers,
        _wires
    )

    for mod in modules:
        if not mod.table.is_in_db(cur):
            mod.table.add_to_db(cur)
        elif not mod.table.is_ok(cur):
            mod.table.update_fields(cur)
