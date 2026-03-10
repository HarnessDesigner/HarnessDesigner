

def cavities(con, cur):
    # cavities point positions are relitive to the housing with the
    # housing being centered at x=0, y=0, z=0

    cur.execute('CREATE TABLE cavities('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'housing_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'point2d TEXT DEFAULT "[0.0, 0.0]" NOT NULL, '                
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'length REAL DEFAULT "2.0" NOT NULL, '
                'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
                'FOREIGN KEY (housing_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()
