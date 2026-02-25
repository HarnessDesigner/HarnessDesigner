

'''

# calculating core diameter
# core_diameter = core_wire_diameter * factor
core_diameter_factors = {
    1: _decimal(1.0),
    2: _deimal(2.0),
    3: _decimal(2.15),
    4: _decimal(2.41),

    # Depending on the wire diameter I don't
    # recommend using more than 4 core wires
    # because of flexability issues
    5: _decimal(2.7),
    6: _decimal(3.0),
    7: _decimal(3.0)
}


import python_utils

def calc_layer_count(od_mm, ll_dia):
    factor = ll_dia / od_mm
    count = 3 * factor + 3
    return int(count)


def create_example(con, cur):

    project_id = 1

    
    INSERT INTO projects (name) VALUES ("Example");
    INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);
    INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);
    INSERT INTO pjt_circuits (project_id, circuit_num, name, description, load, volts, voltage_drop) VALUES (?, ?, ?, ?, ?, ?, ?);
    INSERT INTO pjt_bundle_layouts (project_id, point_id) VALUES (?, ?);
    INSERT INTO pjt_wire3d_layouts (project_id, point_id) VALUES (?, ?);
    INSERT INTO pjt_wire2d_layouts (project_id, point_id) VALUES (?, ?);
    
    INSERT INTO pjt_bundles (project_id, part_id, start_point_id, stop_point_id) VALUES (?, ?, ?, ?);
    INSERT INTO pjt_seals (project_id, part_id, terminal_id) VALUES (?, ?, ?);
    INSERT INTO pjt_cpa_locks (project_id, part_id, housing_id) VALUES (?, ?, ?);
    INSERT INTO pjt_tpa_locks (project_id, part_id, housing_id) VALUES (?, ?, ?);
    INSERT INTO pjt_splices (project_id, part_id, circuit_id, point3d_id, point2d_id) VALUES (?, ?, ?, ?, ?);
    
    INSERT INTO pjt_housings (project_id, part_id, name, point3d_id, point2d_id, quat, angle, angle_reference) VALUES (?, ?, ?, ?, ?);
    INSERT INTO pjt_cavities (project_id, part_id, housing_id, name, start_point2d_id, end_point2d_id, width2d, start_point3d_id, end_point3d_id, length3d, width3d, height3d, diameter3d) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    INSERT INTO pjt_terminals (project_id, part_id, cavity_id, circuit_id, point3d_id, point2d_id, quat, angle) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    INSERT INTO pjt_transitions (project_id, part_id, name, center_id, quat, angle_reference) VALUES (?, ?, ?, ?, ?, ?);
    INSERT INTO pjt_wires (project_id, part_id, circuit_id, start_point3d_id, stop_point3d_id, is_visible) VALUES (?, ?, ?, ?, ?, ?);

'''

