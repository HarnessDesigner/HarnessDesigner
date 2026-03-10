

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

