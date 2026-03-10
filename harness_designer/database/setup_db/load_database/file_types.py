from ... import db_connectors as _con


def add_file_types(con, cur, splash):
    res = cur.execute('SELECT id FROM file_types WHERE id=1;')
    if res.fetchall():
        return

    data = (
        ['image/apng', 'apng', 'APNG', 0],
        ['image/png', 'png', 'PNG', 0],
        ['image/gif', 'gif', 'GIF', 0],
        ['application/jpg', 'jpg', 'JPG', 0],
        ['image/jpg', 'jpg', 'JPG', 0],
        ['application/x-jpg', 'jpg', 'JPG', 0],
        ['image/jpeg', 'jpeg', 'JPEG', 0],
        ['image/pjpg', 'pjpg', 'PJPG', 0],
        ['image/jpe', 'jpe', 'JPE', 0],
        ['image/x-jpf', 'jpf', 'JPF', 0],
        ['image/x-jp2', 'jp2', 'JPEG 2000 JP2', 0],
        ['image/jp2', 'jp2', 'JPEG 2000 JP2', 0],
        ['image/jpx', 'jpx', 'JPEG 2000 JPX', 0],
        ['image/jpm', 'jpm', 'JPEG 2000 JPM', 0],
        ['image/tiff', 'tiff', 'TIFF', 0],
        ['image/tif', 'tif', 'TIF', 0],
        ['image/bmp', 'bmp', 'BMP', 0],
        ['image/x-ms-bmp', 'dib', 'DIB', 0],
        ['image/pdf', 'pdf', 'PDF', 0],
        ['application/pdf', 'pdf', 'PDF', 0],
        ['image/webp', 'webp', 'WEBp', 0],
        ['image/x-dxf', 'dxf', 'DXF', 0],
        ['image/vnd.dxf', 'dxf', 'DXF', 0],
        ['application/dxf', 'dxf', 'DXF', 0],
        ['model/3mf', '3mf', '3MF', 1],
        ['model/gltf-binary', 'gltf', 'GLTF', 1],
        ['model/gltf+json', 'gltf', 'GLTF', 1],
        ['model/iges', 'iges', 'IGES', 1],
        ['', 'igs', 'IGES', 1],
        ['model/vnd.collada+xml', 'dae', 'Collada', 1],
        ['model/obj', '.obj', 'OBJ', 1],
        ['model/step', 'step', 'STEP', 1],
        ['model/step+xml', 'step', 'STEP', 1],
        ['', 'stp', 'STEP', 1],
        ['model/stl', '.stl', 'STL', 1],
        ['model/vrml', 'vrml', 'VRML', 1],
        ['', 'wrl', 'VRML', 1],
        ['model/x3d-vrml', 'x3d', 'X3D', 1],
        ['model/x3d+xml', 'x3d', 'X3D', 1],
        ['application/gltf-buffer', 'gltf', 'GLTF', 1],
        ['application/iges', 'iges', 'IGES', 1],
        ['', 'mdl', '3D GameStudio', 1],
        ['', 'hmp', '3D GameStudio', 1],
        ['', '3ds', '3D Studio Max', 1],
        ['', 'ase', '3D Studio Max', 1],
        ['', 'ac', 'AC3D', 1],
        ['', 'ac3d', 'AC3D', 1],
        ['', 'dxf', 'Autodesk/AutoCAD DXF', 1],
        ['', 'bvh', 'Biovision BVH', 1],
        ['', 'blend', 'Blender BVH', 1],
        ['', 'csm', 'CharacterStudio Motion', 1],
        ['', 'x', 'DirectX X', 1],
        ['', 'md5mesh', 'Doom 3', 1],
        ['', 'md5anim', 'Doom 3', 1],
        ['', 'md5camera', 'Doom 3', 1],
        ['', 'fbx', 'FBX-Format', 1],
        ['', 'ifc', 'IFC-STEP', 1],
        ['', 'irr', 'Irrlicht Mesh/Scene', 1],
        ['', 'irrmesh', 'Irrlicht Mesh/Scene', 1],
        ['', 'lwo', 'LightWave Model/Scene', 1],
        ['', 'lws', 'LightWave Model/Scene', 1],
        ['', 'ms3d', 'Milkshape 3D', 1],
        ['', 'lxo', 'Modo Model', 1],
        ['', 'nff', 'Neutral File Format', 1],
        ['', 'off', 'Object File Format', 1],
        ['', 'mesh.xml', 'Ogre', 1],
        ['', 'skeleton.xml', 'Ogre', 1],
        ['', 'ogex', 'OpenGEX-Fomat', 1],
        ['', 'mdl', 'Quake I', 1],
        ['', 'md2', 'Quake II', 1],
        ['', 'md3', 'Quake III', 1],
        ['', 'pk3', 'Quake 3BSP', 1],
        ['', 'q3o', 'Quick3D', 1],
        ['', 'q3s', 'Quick3D', 1],
        ['', 'raw', 'Raw Triangles', 1],
        ['', 'mdc', 'RtCW', 1],
        ['', 'nff', 'Sense8 WorldToolkit', 1],
        ['', 'ply', 'Polygon File Format', 1],
        ['', 'ter', 'Terragen Terrain', 1],
        ['', 'cob', 'TrueSpace', 1],
        ['', 'scn', 'TrueSpace', 1],
        ['', 'smd', 'Valve Model', 1],
        ['', 'vta', 'Valve Model', 1],
        ['', 'xgl', 'XGL-3D-Format', 1],
        ['', 'amf', 'Additive Manufacturing', 1],
        ['', 'assbin', 'ASSBIN', 1],
        ['', 'b3d', 'OpenBVE 3D', 1],
        ['', 'iqm', 'Inter-Quake Model', 1],
        ['', 'ndo', '3D Low-polygon Modeler', 1],
        ['', 'q3d', 'Quest3D', 1],
        ['', 'sib', 'Silo Model Format', 1],
        ['', 'x3d', 'Extensible 3D', 1],
        ['', 'x3db', 'Extensible 3D', 1],
        ['', 'x3dz', 'Extensible 3D', 1],
        ['', 'x3dbz', 'Extensible 3D', 1],
        ['', 'pmd', 'MikuMikuDance Format', 1],
        ['', 'pmx', 'MikuMikuDance Format', 1]
    )

    splash.SetText(f'Adding file types to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO file_types (mimetype, extension, name, is_model) '
                    'VALUES (?, ?, ?, ?);', data)
    splash.SetText(f'Adding file types to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_file_type(con, cur, extension=None, mimetype=None):
    if extension is None and mimetype is None:
        return None

    if extension is not None and mimetype is not None:
        res = cur.execute(f'SELECT id FROM file_types WHERE extension="{extension}" AND mimetype="{mimetype}";').fetchall()

        if res:
            return res[0][0]

        print(f'DATABASE: adding file type ("{extension}", "{mimetype}")')

        cur.execute('INSERT INTO file_types (extension, mimetype) VALUES (?, ?);', (extension, mimetype))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: file type added "{extension}" = {db_id}')

        return db_id

    elif extension is not None:
        res = cur.execute(f'SELECT id FROM file_types WHERE extension="{extension}";').fetchall()

        if res:
            return res[0][0]

        print(f'DATABASE: adding file type ("{extension}")')

        cur.execute('INSERT INTO file_types (extension,) VALUES (?);', (extension,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: file type added "{extension}" = {db_id}')

        return db_id

    elif mimetype is not None:
        res = cur.execute(f'SELECT id FROM file_types WHERE mimetype="{mimetype}";').fetchall()

        if res:
            return res[0][0]

        return None


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'file_types',
    id_field,
    _con.TextField('extension', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('mimetype', default='""', no_null=True),
    _con.IntField('is_model', default='1', no_null=True)

)


# def file_types(con, cur):
#     cur.execute('CREATE TABLE file_types('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'extension TEXT, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'mimetype TEXT DEFAULT "" NOT NULL, '
#                 'is_model INTEGER DEFAULT 1 NOT NULL'
#                 ');')
#     con.commit()
