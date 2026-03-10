



# ===================== assemblies =====================

# assemblies are housings that include all related parts and pieces.
# These are used for things like sensors that get used commonly to make it easier
# when bulding a harness.

def assemblies(con, cur):
    cur.execute('CREATE TABLE assemblies('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL'
                ');')
    con.commit()


def assembly_seals(con, cur):
    cur.execute('CREATE TABLE assembly_seals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point or terminal relative point
                'housing_id INTEGER DEFAULT NULL, '
                'terminal_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES seals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (terminal_id) REFERENCES assembly_terminals(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_boots(con, cur):
    cur.execute('CREATE TABLE assembly_boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES boots(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_covers(con, cur):
    cur.execute('CREATE TABLE assembly_covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES covers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_cpa_locks(con, cur):
    cur.execute('CREATE TABLE assembly_cpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES cpa_locks(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_tpa_locks(con, cur):
    cur.execute('CREATE TABLE assembly_tpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES tpa_locks(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_housings(con, cur):
    cur.execute('CREATE TABLE assembly_housings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'cover_point3d_id INTEGER NOT NULL, '  # relative to housing, for cover to snap onto
                'seal_point3d_id INTEGER NOT NULL, '  # relative to housing, for seal to snap onto
                'boot_point3d_id INTEGER NOT NULL, '  # relative to housing, for boot to snap onto
                'tpa_lock_1_point3d_id INTEGER NOT NULL, '  # relative to housing, for the first tpa lock to snap onto
                'tpa_lock_2_point3d_id INTEGER NOT NULL, '  # relative to housing, for a second tpa lock to snap onto
                'cpa_lock_point3d_id INTEGER NOT NULL, '  # relative to housing, for cpa lock to snap onto
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cover_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (seal_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (boot_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (tpa_lock_1_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (tpa_lock_2_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cpa_lock_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_cavities(con, cur):
    cur.execute('CREATE TABLE assembly_cavities('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER DEFAULT NULL, '
                'housing_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # Relative to housing
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES cavities(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES assembly_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES assembly_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_terminals(con, cur):
    cur.execute('CREATE TABLE assembly_terminals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'cavity_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # will snap to a cavity point
                'wire_point3d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'wire_point2d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'is_start INTEGER DEFAULT 0 NOT NULL, '
                'volts REAL DEFAULT "0.0" NOT NULL, '
                'load REAL DEFAULT "0.0" NOT NULL, '
                'voltage_drop REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES terminals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_id) REFERENCES assembly_cavities(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (wire_point3d_id) REFERENCES assembly_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES assembly_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


# ================ project tables ======================
def projects(con, cur):
    cur.execute('CREATE TABLE projects('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL, '
                'user_model TEXT DEFAULT "" NOT NULL, '
                'creator TEXT DEFAULT "" NOT NULL, '
                'object_count INTEGER DEFAULT 0 NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()


def pjt_points3d(con, cur):
    cur.execute('CREATE TABLE pjt_points3d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'x REAL DEFAULT "0.0" NOT NULL, '
                'y REAL DEFAULT "0.0" NOT NULL, '
                'z REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_points2d(con, cur):
    cur.execute('CREATE TABLE pjt_points2d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'x REAL DEFAULT "0.0" NOT NULL, '
                'y REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_circuits(con, cur):
    cur.execute('CREATE TABLE pjt_circuits('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'circuit_num INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_bundle_layouts(con, cur):
    cur.execute('CREATE TABLE pjt_bundle_layouts('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, share with bundle
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id)'
                ');')
    con.commit()


def pjt_wire_layouts(con, cur):
    cur.execute('CREATE TABLE pjt_wire_layouts('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'point3d_id INTEGER DEFAULT NULL, '  # absolute, shared with wire
                'point2d_id INTEGER DEFAULT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_concentrics(con, cur):
    cur.execute('CREATE TABLE pjt_concentrics('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'bundle_id INTEGER DEFAULT NULL, '
                'transition_branch_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (bundle_id) REFERENCES pjt_bundles(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (transition_branch_id) REFERENCES pjt_transition_branches(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_concentric_layers(con, cur):
    cur.execute('CREATE TABLE pjt_concentric_layers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'diameter REAL DEFULT "0.0" NOT NULL, '
                'num_wires INTEGER DEFAULT 0 NOT NULL, '
                'num_fillers INTEGER DEFAULT 0 NOT NULL, '
                'concentric_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (concentric_id) REFERENCES pjt_concentrics(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_concentric_wires(con, cur):
    cur.execute('CREATE TABLE pjt_concentric_wires('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'layer_id INTEGER NOT NULL, '
                'wire_id INTEGER NOT NULL, '
                'point_id INTEGER NOT NULL, '
                'is_filler INTEGER DEFAULT 0 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (layer_id) REFERENCES pjt_concentric_layers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (wire_id) REFERENCES pjt_wires(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point_id) REFERENCES pjt_point2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_bundles(con, cur):
    cur.execute('CREATE TABLE pjt_bundles('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'start_point3d_id INTEGER NOT NULL, '  # absolute, can be shared with a bundle layout or transition
                'stop_point3d_id INTEGER NOT NULL, '  # absolute, can be shared with a bundle layout or transition
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES bundle_covers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (start_point3d_id) REFERENCES pjt_points3d(id), '
                'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_points3d(id)'
                ');')
    con.commit()


def pjt_seals(con, cur):
    cur.execute('CREATE TABLE pjt_seals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point or terminal relative point
                'housing_id INTEGER DEFAULT NULL, '
                'terminal_id INTEGER DEFAULT NULL, '
                'cavity_id INTEGER DEFAULT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES seals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_id) REFERENCES pjt_cavities(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (terminal_id) REFERENCES pjt_terminals(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_boots(con, cur):
    cur.execute('CREATE TABLE pjt_boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES boots(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_covers(con, cur):
    cur.execute('CREATE TABLE pjt_covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES covers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_cpa_locks(con, cur):
    cur.execute('CREATE TABLE pjt_cpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES cpa_locks(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_tpa_locks(con, cur):
    cur.execute('CREATE TABLE pjt_tpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
                'housing_id INTEGER DEFAULT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES tpa_locks(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_splices(con, cur):
    cur.execute('CREATE TABLE pjt_splices('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'circuit_id INTEGER DEFAULT NULL, '
                'start_point3d_id INTEGER NOT NULL, '  # absolute
                'stop_point3d_id INTEGER NOT NULL, '  # absolute
                'branch_point3d_id INTEGER NOT NULL, '  # absolute
                'point2d_id INTEGER NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES splices(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (start_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (branch_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_housings(con, cur):
    cur.execute('CREATE TABLE pjt_housings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'cover_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for cover to snap onto
                'seal_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for seal to snap onto
                'boot_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for boot to snap onto
                'tpa_lock_1_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for the first tpa lock to snap onto
                'tpa_lock_2_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for a second tpa lock to snap onto
                'cpa_lock_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for cpa lock to snap onto
                'point3d_id INTEGER DEFAULT NULL, '  # absolute
                'point2d_id INTEGER DEFAULT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cover_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (seal_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (boot_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (tpa_lock_1_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (tpa_lock_2_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cpa_lock_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_cavities(con, cur):
    cur.execute('CREATE TABLE pjt_cavities('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER DEFAULT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'housing_id INTEGER NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # Relative to housing
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES cavities(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_terminals(con, cur):
    cur.execute('CREATE TABLE pjt_terminals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'cavity_id INTEGER NOT NULL, '
                'circuit_id INTEGER DEFAULT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # will snap to a cavity point
                'wire_point3d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'wire_point2d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'is_start INTEGER DEFAULT 0 NOT NULL, '
                'volts REAL DEFAULT "0.0" NOT NULL, '
                'load REAL DEFAULT "0.0" NOT NULL, '
                'voltage_drop REAL DEFAULT "0.0" NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES terminals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_id) REFERENCES pjt_cavities(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (circuit_id) REFERENCES pjt_circuits(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (wire_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_transition_branches(con, cur):
    cur.execute('CREATE TABLE pjt_transition_branches('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'branch_id INTEGER NOT NULL, '
                'transition_id INTEGER NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # can be shared with a bundle cover
                'diameter REAL DEFAULT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (transition_id) REFERENCES pjt_transitions(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_transitions(con, cur):
    cur.execute('CREATE TABLE pjt_transitions('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES terminals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_wires(con, cur):
    cur.execute('CREATE TABLE pjt_wires('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'circuit_id INTEGER DEFAULT NULL, '
                'bundle_id INTEGER DEFAULT NULL, '
                'transition_id INTEGER DEFAULT NULL, '
                'start_point3d_id INTEGER NOT NULL, '  # can be shared with a wire layout or terminal
                'stop_point3d_id INTEGER NOT NULL, '  # can be shared with a wire layout or terminal
                'start_point2d_id INTEGER NOT NULL, '
                'stop_point2d_id INTEGER NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1, '
                'is_visible3d INTEGER DEFAULT 1, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES wires(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (circuit_id) REFERENCES pjt_circuits(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (bundle_id) REFERENCES pjt_bundles(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (transition_id) REFERENCES pjt_transitions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (start_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (start_point2d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (stop_point2d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_notes(con, cur):
    cur.execute('CREATE TABLE pjt_notes('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'point2d_id INTEGER DEFAULT NULL, '
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'size2d INTEGER NOT NULL, '
                'h_align2d INTEGER NOT NULL, '
                'v_align2d INTEGER NOT NULL, '
                'style2d INTEGER NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'point3d_id INTEGER DEFAULT NULL, '  # absolute
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'size3d REAL NOT NULL, '
                'h_align3d INTEGER NOT NULL, '
                'v_align3d INTEGER NOT NULL, '
                'style3d INTEGER NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'note TEXT DEFAULT "" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_wire_markers(con, cur):
    cur.execute('CREATE TABLE pjt_wire_markers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'point2d_id INTEGER DEFAULT NULL, '
                'point3d_id INTEGER DEFAULT NULL, '  # absolute but must be on a wire
                'part_id INTEGER NOT NULL, '
                'wire_id INTEGER NOT NULL, '
                'label TEXT DEFAULT "" NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES wire_markers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (wire_id) REFERENCES pjt_wires(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_wire_service_loops(con, cur):
    cur.execute('CREATE TABLE pjt_wire_service_loops('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'start_point3d_id INTEGER NOT NULL, '  # can be shared with a terminal or wire_layout
                'stop_point3d_id INTEGER NOT NULL, '  # can be shared with a terminal or wire layout
                'part_id INTEGER NOT NULL, '
                'circuit_id INTEGER NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (start_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES wires(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (circuit_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE'');')
    con.commit()


def global_table_mapping():
    mapping = (
        ('resources', resources),
        ('manufacturers', manufacturers),
        ('temperatures', temperatures),
        ('genders', genders),
        ('protections', protections),
        ('adhesives', adhesives),
        ('cavity_locks', cavity_locks),
        ('colors', colors),
        ('directions', directions),
        ('ip_fluids', ip_fluids),
        ('ip_solids', ip_solids),
        ('ip_supps', ip_supps),
        ('platings', platings),
        ('materials', materials),
        ('shapes', shapes),
        ('series', series),
        ('families', families),
        ('ip_ratings', ip_ratings),
        ('accessories', accessories),
        ('transition_series', transition_series),
        ('transitions', transitions),
        ('transition_branches', transition_branches),
        ('boots', boots),
        ('bundle_covers', bundle_covers),
        ('covers', covers),
        ('cpa_locks', cpa_locks),
        ('tpa_locks', tpa_locks),
        ('seal_types', seal_types),
        ('seals', seals),
        ('wire_markers', wire_markers),
        ('wires', wires),
        ('terminals', terminals),
        ('settings', settings),
        ('splice_types', splice_types),
        ('splices', splices),
        ('file_types', file_types),
        ('models3d', models3d),
        ('housings', housings),
        ('cavities', cavities),
    )

    for name, fnc in mapping:
        yield name, fnc


def crossref_table_mapping():
    mapping = (
        ('housing_crossref', housing_crossref),
        ('terminal_crossref', terminal_crossref),
        ('seal_crossref', seal_crossref),
        ('cover_crossref', cover_crossref),
        ('boot_crossref', boot_crossref),
        ('tpa_lock_crossref', tpa_lock_crossref),
        ('cpa_lock_crossref', cpa_lock_crossref)
    )

    for name, fnc in mapping:
        yield name, fnc


def project_table_mapping():
    mapping = (
        ('projects', projects),
        ('pjt_points3d', pjt_points3d),
        ('pjt_points2d', pjt_points2d),
        ('pjt_circuits', pjt_circuits),
        ('pjt_bundle_layouts', pjt_bundle_layouts),
        ('pjt_wire_layouts', pjt_wire_layouts),
        ('pjt_concentrics', pjt_concentrics),
        ('pjt_concentric_layers', pjt_concentric_layers),
        ('pjt_concentric_wires', pjt_concentric_wires),
        ('pjt_bundles', pjt_bundles),
        ('pjt_seals', pjt_seals),
        ('pjt_boots', pjt_boots),
        ('pjt_covers', pjt_covers),
        ('pjt_cpa_locks', pjt_cpa_locks),
        ('pjt_tpa_locks', pjt_tpa_locks),
        ('pjt_splices', pjt_splices),
        ('pjt_housings', pjt_housings),
        ('pjt_cavities', pjt_cavities),
        ('pjt_terminals', pjt_terminals),
        ('pjt_transition_branches', pjt_transition_branches),
        ('pjt_transitions', pjt_transitions),
        ('pjt_wires', pjt_wires),
        ('pjt_notes', pjt_notes),
        ('pjt_wire_markers', pjt_wire_markers),
        ('pjt_wire_service_loops', pjt_wire_service_loops)
    )

    for name, fnc in mapping:
        yield name, fnc


if __name__ == '__main__':
    import sqlite3
    import os
    import sys

    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessDesigner')
    else:
        app_data = '.HarnessDesigner'

    app_data = os.path.join(user_profile, app_data)

    if not os.path.exists(app_data):
        os.mkdir(app_data)

    con_ = sqlite3.connect(os.path.join(app_data, 'harness_designer.db'))
    cur_ = con_.cursor()

    cur_.execute('PRAGMA foreign_keys = ON;')
    con_.commit()

    funcs = (
        resources,
        manufacturers,
        temperatures,
        genders,
        protections,
        adhesives,
        cavity_locks,
        colors,
        directions,
        ip_fluids,
        ip_solids,
        ip_supps,
        platings,
        materials,
        shapes,
        series,
        families,
        ip_ratings,
        accessories,
        transition_series,
        transitions,
        transition_branches,
        boots,
        bundle_covers,
        covers,
        cpa_locks,
        tpa_locks,
        seal_types,
        seals,
        wire_markers,
        wires,
        terminals,
        settings,
        splice_types,
        splices,
        file_types,
        models3d,
        housings,
        cavities,
        # housing_crossref,
        # terminal_crossref,
        # seal_crossref,
        # cover_crossref,
        # boot_crossref,
        # tpa_lock_crossref,
        # cpa_lock_crossref,
        assemblies,
        assembly_seals,
        assembly_boots,
        assembly_covers,
        assembly_cpa_locks,
        assembly_tpa_locks,
        assembly_housings,
        assembly_cavities,
        assembly_terminals,
        projects,
        pjt_points3d,
        pjt_points2d,
        pjt_circuits,
        pjt_bundle_layouts,
        pjt_wire_layouts,
        pjt_concentrics,
        pjt_concentric_layers,
        pjt_concentric_wires,
        pjt_bundles,
        pjt_seals,
        pjt_boots,
        pjt_covers,
        pjt_cpa_locks,
        pjt_tpa_locks,
        pjt_splices,
        pjt_housings,
        pjt_cavities,
        pjt_terminals,
        pjt_transition_branches,
        pjt_transitions,
        pjt_wires,
        pjt_notes,
        pjt_wire_markers,
        pjt_wire_service_loops
    )

    for func in funcs:
        func(con_, cur_)

    cur_.close()
    con_.close()
