
def resources(con, cur):
    cur.execute('CREATE TABLE resources('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'path TEXT DEFAULT "" NOT NULL, '
                'type TEXT DEFAULT "UNKNOWN", '
                'data BLOB DEFAULT NULL'
                ');')
    con.commit()


def manufacturers(con, cur):
    cur.execute('CREATE TABLE manufacturers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'address TEXT DEFAULT "" NOT NULL, '
                'contact_person TEXT DEFAULT "" NOT NULL, '
                'phone TEXT DEFAULT "" NOT NULL, '
                'ext TEXT DEFAULT "" NOT NULL, '
                'email TEXT DEFAULT "" NOT NULL, '
                'website TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()


def temperatures(con, cur):
    cur.execute('CREATE TABLE temperatures('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def genders(con, cur):
    cur.execute('CREATE TABLE genders('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def protections(con, cur):
    cur.execute('CREATE TABLE protections('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL'
                ');')
    con.commit()


def adhesives(con, cur):
    cur.execute('CREATE TABLE adhesives('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'code TEXT DEFAULT "" NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'accessory_part_nums TEXT DEFAULT "[]" NOT NULL'
                ');')
    con.commit()


def cavity_locks(con, cur):
    cur.execute('CREATE TABLE cavity_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()


def colors(con, cur):
    cur.execute('CREATE TABLE colors('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'rgb INTEGER NOT NULL'
                ');')
    con.commit()


def directions(con, cur):
    cur.execute('CREATE TABLE directions('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def ip_fluids(con, cur):
    cur.execute('CREATE TABLE ip_fluids('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'short_desc TEXT NOT NULL, '
                'description TEXT NOT NULL, '
                'icon_data BLOB DEFAULT NULL'                        
                ');')
    con.commit()


def ip_solids(con, cur):
    cur.execute('CREATE TABLE ip_solids('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'short_desc TEXT NOT NULL, '
                'description TEXT NOT NULL, '
                'icon_data BLOB DEFAULT NULL'
                ');')
    con.commit()


def ip_supps(con, cur):
    cur.execute('CREATE TABLE ip_supps('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT NOT NULL'
                ');')
    con.commit()


def platings(con, cur):
    cur.execute('CREATE TABLE platings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'symbol TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()


def materials(con, cur):
    cur.execute('CREATE TABLE materials('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()


def shapes(con, cur):
    cur.execute('CREATE TABLE shapes('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def series(con, cur):
    cur.execute('CREATE TABLE series('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL, '
                'mfg_id INTEGER DEFAULT 1 NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def families(con, cur):
    cur.execute('CREATE TABLE families('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def ip_ratings(con, cur):
    cur.execute('CREATE TABLE ip_ratings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL, '
                'solid_id INTEGER DEFAULT 7 NOT NULL, '
                'fluid_id INTEGER DEFAULT 12 NOT NULL, '
                'supp_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (solid_id) REFERENCES ip_solids(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (fluid_id) REFERENCES ip_fluids(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (supp_id) REFERENCES ip_supps(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def accessories(con, cur):
    cur.execute('CREATE TABLE accessories('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def transition_series(con, cur):
    cur.execute('CREATE TABLE transition_series('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def transitions(con, cur):
    cur.execute('CREATE TABLE transitions('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'transition_series_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'branch_count INTEGER DEFAULT 0 NOT NULL, '
                'shape_id INTEGER DEFAULT 0 NOT NULL, '
                'protection_id INTEGER DEFAULT 0 NOT NULL, '
                'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (transition_series_id) REFERENCES transition_series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (protection_id) REFERENCES protections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def transition_branches(con, cur):
    cur.execute('CREATE TABLE transition_branches('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'transition_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'bulb_offset TEXT DEFAULT NULL, '
                'bulb_length REAL DEFUALT NULL, '
                'min_dia REAL NOT NULL, '
                'max_dia REAL NOT NULL, '
                'length REAL NOT NULL, '
                'offset TEXT DEFAULT NULL, '
                'angle REAL DEFAULT NULL, '
                'flange_height REAL DEFAULT NULL, '
                'flange_width REAL DEFAULT NULL, '
                'FOREIGN KEY (transition_id) REFERENCES transitions(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def boot_shapes(con, cur):
    cur.execute('CREATE TABLE boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def boot_rectangle(con, cur):
    cur.execute('CREATE TABLE boot_rectangle('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'boot_id INTEGER DEFAULT 0 NOT NULL, '
                'min_length REAL NOT NULL, '
                'max_length REAL NOT NULL, '
                'min_width REAL NOT NULL, '
                'max_width REAL NOT NULL, '
                'min_height REAL NOT NULL, '
                'max_height REAL NOT NULL, '
                'bulb_offset TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL,'
                'bundle_dia_min REAL NOT NULL,'
                'bundle_dia_max REAL NOT NULL,'
                'bundle_length REAL NOT NULL,'
                'bundle_angle REAL NOT NULL,'
                'FOREIGN KEY (boot_id) REFERENCES boots(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def boot_circular(con, cur):
    cur.execute('CREATE TABLE boot_rectangle('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'boot_id INTEGER DEFAULT 0 NOT NULL, '
                'min_dia REAL NOT NULL, '
                'max_dia REAL NOT NULL, '
                'bundle_dia_min REAL NOT NULL,'
                'bundle_dia_max REAL NOT NULL,'
                'bulb_offset TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL,'
                'bundle_length REAL NOT NULL,'
                'bundle_angle REAL NOT NULL,'
                'FOREIGN KEY (boot_id) REFERENCES boots(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def boots(con, cur):
    cur.execute('CREATE TABLE boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'direction_id INETGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def bundle_covers(con, cur):
    cur.execute('CREATE TABLE bundle_covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'shrink_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'rigidity TEXT DEFAULT "NOT SET" NOT NULL, '
                'shrink_ratio TEXT DEFAULT "" NOT NULL, '
                'wall TEXT DEFAULT "Single" NOT NULL, '
                'min_dia INTEGER DEFAULT 0 NOT NULL, '
                'max_dia INTEGER DEFAULT 0 NOT NULL, '
                'protection_id TEXT DEFAULT 0 NOT NULL, '
                'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (protection_id) REFERENCES potections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (shrink_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def covers(con, cur):
    cur.execute('CREATE TABLE covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '       
                'direction_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'pins TEXT DEFAULT "" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def cpa_locks(con, cur):
    cur.execute('CREATE TABLE cpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'pins TEXT DEFAULT "" NOT NULL, '
                'terminal_size REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def tpa_locks(con, cur):
    cur.execute('CREATE TABLE tpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'pins TEXT DEFAULT "" NOT NULL, '
                'terminal_size REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def seal_types(con, cur):
    cur.execute('CREATE TABLE seal_types('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL);')
    con.commit()


def seals(con, cur):
    cur.execute('CREATE TABLE seals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 999999 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, ' 
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '     
                'type_id INTEGER DEFAULT 0 NOT NULL, '
                'hardness INTEGER DEFAULT -1 NOT NULL, '
                'lubricant TEXT DEFAULT "" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'o_dia REAL DEFAULT "0.0" NOT NULL, '
                'i_dia REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '   
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '    
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (type_id) REFERENCES seal_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '    
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'                
                ');')
    con.commit()


def wire_markers(con, cur):
    cur.execute('CREATE TABLE wire_markers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'min_diameter REAL DEFAULT "0.0" NOT NULL, '
                'max_diameter REAL DEFAULT "0.0" NOT NULL, '
                'min_awg INTEGER DEFAULT NULL, '
                'max_awg INTEGER DEFAULT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'has_label INTEGER DEFAULT 0 NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def wires(con, cur):
    cur.execute('CREATE TABLE wires('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'stripe_color_id INTEGER DEFAULT 999999 NOT NULL, '
                'num_conductors INTEGER DEFAULT 1 NOT NULL, '
                'shielded INTEGER DEFAULT 0 NOT NULL, '
                'tpi REAL DEFAULT "0.0" NOT NULL, '
                'conductor_dia_mm REAL DEFAULT NULL, '
                'size_mm2 REAL DEFAULT NULL, '
                'size_awg INTEGER DEFAULT NULL, '
                'od_mm REAL NOT NULL, '
                'weight_1km REAL DEFAULT "0.0" NOT NULL, '
                'core_material_id INTEGER DEFAULT 0 NOT NULL, '
                'resistance_1km REAL DEFAULT "0.0" NOT NULL, '
                'volts REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (stripe_color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (core_material_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def terminals(con, cur):
    cur.execute('CREATE TABLE terminals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'plating_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'gender_id INTEGER DEFAULT 0 NOT NULL, '
                'sealing INTEGER DEFAULT 0 NOT NULL, '
                'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '                
                'blade_size REAL DEFAULT "0.0" NOT NULL, '
                'resistance REAL DEFAULT "0.0" NOT NULL, '
                'mating_cycles INTEGER DEFAULT 0 NOT NULL, '
                'max_vibration_g INTEGER DEFAULT 0 NOT NULL, '
                'max_current_ma INTEGER DEFAULT 0 NOT NULL, '
                'wire_size_min_awg INTEGER DEFAULT 20 NOT NULL, '
                'wire_size_max_awg INTEGER DEFAULT 20 NOT NULL, '
                'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '
                'min_wire_cross REAL DEFAULT "0.0" NOT NULL, '
                'max_wire_cross REAL DEFAULT "0.0" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_lock_id) REFERENCES cavity_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'                               
                ');')
    con.commit()


def settings(con, cur):
    cur.execute('CREATE TABLE settings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'value BLOB NOT NULL'
                ');')
    con.commit()


def splice_types(con, cur):
    cur.execute('CREATE TABLE splice_types('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()


def splices(con, cur):
    cur.execute('CREATE TABLE splices('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'plating_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'type_id INTEGER DEFAULT 0 NOT NULL, '
                'min_dia REAL DEFAULT "0.0" NOT NULL, '
                'max_dia REAL DEFAULT "0.0" NOT NULL, '
                'resistance REAL DEFAULT "0.0" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '  
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (type_id) REFERENCES splice_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    
    con.commit()


def models3d(con, cur):
    cur.execute('CREATE TABLE models3d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'idx INTEGER DEFAULT 0 NOT NULL, '
                'type TEXT DEFAULT "" NOT NULL, '
                'target_count INTEGER DEFAULT 25000 NOT NULL, '
                'agressive REAL DEFAULT "5.0" NOT NULL, '
                'path TEXT DEFAULT NULL, '
                'data BLOB DEFAULT NULL, '
                'offset TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'angle TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL'
                ');')
    
    con.commit()


def housings(con, cur):
    cur.execute('CREATE TABLE housings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '                    
                'gender_id INTEGER DEFAULT 0 NOT NULL, '
                'direction_id INTEGER DEFAULT 0 NOT NULL, '    
                'image_id INTEGER DEFAULT 0 NOT NULL, '
                'datasheet_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '                   
                'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '
                'sealing INTEGER DEFAULT 0 NOT NULL, '
                'rows INTEGER DEFAULT 0 NOT NULL, '    
                'num_pins INTEGER DEFAULT 0 NOT NULL, '
                'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
                'terminal_size_counts TEXT DEFAULT "[]" NOT NULL,'
                'centerline REAL DEFAULT "0.0" NOT NULL, '
                'compat_cpas TEXT DEFAULT "[]" NOT NULL, '    
                'compat_tpas TEXT DEFAULT "[]" NOT NULL, '    
                'compat_covers TEXT DEFAULT "[]" NOT NULL, '    
                'compat_terminals TEXT DEFAULT "[]" NOT NULL, '    
                'compat_seals TEXT DEFAULT "[]" NOT NULL, '
                'compat_housings TEXT DEFAULT "[]" NOT NULL, '
                'ip_rating_id INTEGER DEFAULT 0 NOT NULL, '                
                'cavitymap_id INTEGER DEFAULT 0 NOT NULL, '               
                'cavitymap_overlay_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'footprint_id INTEGER DEFAULT 0 NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (ip_rating_id) REFERENCES ip_ratings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (cavity_lock_id) REFERENCES terminal_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (cavitymap_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cavitymap_overlay_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'  
                ');')
    con.commit()


def cavity_points2d(con, cur):
    # cavities point positions are relitive to the housing with the
    # housing being centered at x=0, y=0, z=0

    cur.execute('CREATE TABLE cavity_points2d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'x REAL NOT NULL, '
                'y REAL NOT NULL'
                ');')
    con.commit()


def cavity_points3d(con, cur):
    # cavities point positions are relitive to the housing with the
    # housing being centered at x=0, y=0, z=0

    cur.execute('CREATE TABLE cavity_points3d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'x REAL NOT NULL, '
                'y REAL NOT NULL, '
                'z REAL NOT NULL'
                ');')
    con.commit()


def cavities(con, cur):
    # cavities point positions are relitive to the housing with the
    # housing being centered at x=0, y=0, z=0

    cur.execute('CREATE TABLE cavities('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'housing_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'point2d_id INTEGER DEFAULT NULL, '                
                'point3d_id INTEGER DEFAULT NULL, '
                'quat TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'length REAL DEFAULT "2.0" NOT NULL, '
                'terminal_size REAL DEFAULT NULL, '
                'FOREIGN KEY (housing_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES cavity_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES cavity_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def housing_crossref(con, cur):
    cur.execute('CREATE TABLE housing_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'housing_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'housing_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (housing_id1) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id2) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def terminal_crossref(con, cur):
    cur.execute('CREATE TABLE terminal_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'terminal_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'terminal_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (terminal_id1) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (terminal_id2) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def seal_crossref(con, cur):
    cur.execute('CREATE TABLE seal_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'seal_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'seal_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (seal_id1) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (seal_id2) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def cover_crossref(con, cur):
    cur.execute('CREATE TABLE cover_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'cover_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'cover_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (cover_id1) REFERENCES covers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cover_id2) REFERENCES covers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def boot_crossref(con, cur):
    cur.execute('CREATE TABLE boot_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'boot_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'boot_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (boot_id1) REFERENCES booth(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (boot_id2) REFERENCES boots(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def tpa_lock_crossref(con, cur):
    cur.execute('CREATE TABLE tpa_lock_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'tpa_lock_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'tpa_lock_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (tpa_lock_id1) REFERENCES tpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (tpa_lock_id2) REFERENCES tpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


def cpa_lock_crossref(con, cur):
    cur.execute('CREATE TABLE cpa_lock_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'cpa_lock_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'cpa_lock_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (cpa_lock_id1) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cpa_lock_id2) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


# ===================== assemblies =====================

# assemblies are housings that include all related parts and pieces.
# These are used for things like sensors that get used commonly to make it easier
# when bulding a harness.

def assemblies(con, cur):
    cur.execute('CREATE TABLE assemblies('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT NOT NULL, '
                ');')
    con.commit()


def assembly_points3d(con, cur):
    cur.execute('CREATE TABLE assembly_points3d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'x REAL DEFAULT "0.0" NOT NULL, '
                'y REAL DEFAULT "0.0" NOT NULL, '
                'z REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def assembly_points2d(con, cur):
    cur.execute('CREATE TABLE assembly_points2d('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'assembly_id INTEGER NOT NULL, '
                'x REAL DEFAULT "0.0" NOT NULL, '
                'y REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (assembly_id) REFERENCES assemblies(id) ON DELETE CASCADE ON UPDATE CASCADE'
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
                'FOREIGN KEY (cpa_lock_point3d_id) REFERENCES assembly_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
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
                'object_count INTEGER DEFAULT 0 NOT NULL'
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
                'description TEXT DEFAULT "" NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_bundle_layouts(con, cur):
    cur.execute('CREATE TABLE pjt_bundle_layouts('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point or terminal relative point
                'housing_id INTEGER DEFAULT NULL, '
                'terminal_id INTEGER DEFAULT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES seals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (terminal_id) REFERENCES pjt_terminals(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()


def pjt_boots(con, cur):
    cur.execute('CREATE TABLE pjt_boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'cover_point3d_id INTEGER NOT NULL, '  # relative to housing, for cover to snap onto
                'seal_point3d_id INTEGER NOT NULL, '  # relative to housing, for seal to snap onto
                'boot_point3d_id INTEGER NOT NULL, '  # relative to housing, for boot to snap onto
                'tpa_lock_1_point3d_id INTEGER NOT NULL, '  # relative to housing, for the first tpa lock to snap onto
                'tpa_lock_2_point3d_id INTEGER NOT NULL, '  # relative to housing, for a second tpa lock to snap onto
                'cpa_lock_point3d_id INTEGER NOT NULL, '  # relative to housing, for cpa lock to snap onto
                'point3d_id INTEGER NOT NULL, '  # absolute
                'point2d_id INTEGER NOT NULL, '
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'housing_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # Relative to housing
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'cavity_id INTEGER NOT NULL, '
                'circuit_id INTEGER DEFAULT NULL, '
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
                'angle2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'size2d INTEGER NOT NULL, '
                'h_align2d INTEGER NOT NULL, '
                'v_align2d INTEGER NOT NULL, '
                'style2d INTEGER NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'point3d_id INTEGER DEFAULT NULL, '  # absolute
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '    
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
                'angle3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
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
        ('splice_types', splice_types),
        ('splices', splices),
        ('models3d', models3d),
        ('housings', housings),
        ('cavity_points2d', cavity_points2d),
        ('cavity_points3d', cavity_points3d),
        ('cavities', cavities),
        ('settings', settings)
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
        ('pjt_boots', pjt_boots),
        ('pjt_covers', pjt_covers),
        ('pjt_bundles', pjt_bundles),
        ('pjt_seals', pjt_seals),
        ('pjt_cpa_locks', pjt_cpa_locks),
        ('pjt_tpa_locks', pjt_tpa_locks),
        ('pjt_splices', pjt_splices),
        ('pjt_housings', pjt_housings),
        ('pjt_cavities', pjt_cavities),
        ('pjt_terminals', pjt_terminals),
        ('pjt_transitions', pjt_transitions),
        ('pjt_wire_markers', pjt_wire_markers),
        ('pjt_wires', pjt_wires),
        ('pjt_wire_service_loops', pjt_wire_service_loops),
        ('pjt_concentrics', pjt_concentrics),
        ('pjt_concentric_layers', pjt_concentric_layers),
        ('pjt_concentric_wires', pjt_concentric_wires),
        ('pjt_transition_branches', pjt_transition_branches),
        ('pjt_notes', pjt_notes)
    )

    for name, fnc in mapping:
        yield name, fnc


if __name__ == '__main__':
    import sqlite3
    con_ = sqlite3.connect('test.db')
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
        splice_types,
        splices,
        models3d,
        housings,
        cavities,
        housing_crossref,
        terminal_crossref,
        seal_crossref,
        cover_crossref,
        boot_crossref,
        tpa_lock_crossref,
        cpa_lock_crossref,
        projects,
        pjt_points3d,
        pjt_points2d,
        pjt_circuits,
        pjt_bundle_layouts,
        pjt_wire_layouts,
        pjt_bundles,
        pjt_seals,
        pjt_cpa_locks,
        pjt_tpa_locks,
        pjt_splices,
        pjt_housings,
        pjt_cavities,
        pjt_terminals,
        pjt_transitions,
        pjt_wire_markers,
        pjt_wires
    )

    for func in funcs:
        func(con_, cur_)

    cur_.close()
    con_.close()
