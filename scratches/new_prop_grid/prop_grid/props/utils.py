

def remap(value: int | float,
          old_min: int | float, old_max: int | float,
          new_min: int | float, new_max: int | float,
          type=float) -> int | float:  # NOQA

    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min

    return type(new_value)


IMAGE_FILE_WILDCARDS = (
    'All Supported Images |*.png;*.bmp;*.jpg;*.jpeg;*.gif;*.tif;*.tiff|'
    "PNG (png)|*.png|"
    "Bitmap (bmp)|*.bmp|"
    "JPEG (jpg, jpeg)|*.jpg;*.jpeg|"
    "GIF (gif)|*.gif|"
    "Tiff (tif, tiff)|*.tif;*.tiff|"
)


MODEL_FILE_WILDCARDS = (
    "All Supported Models |*.3mf;*.glTF;*.igs;*.iges;*.dae;*.obj;*.stp;*.step;"
    "*.stl;*.vrml;*.wrl;*.mdl;*.hmp;*.3ds;*.ase;*.ac;*.ac3d;*.dxf;*.bvh;*.blend;"
    "*.csm;*.x;*.md5mesh;*.md5anim;*.md5camera;*.fbx;*.ifc;*.irr;*.irrmesh;*.lwo;"
    "*.lws;*.ms3d;*.lxo;*.nff;*.off;*.mesh.xml;*.skeleton.xml;*.ogex;*.mdl;*.md2;"
    "*.md3;*.pk3;*.q3o;*.q3s;*.raw;*.mdc;*.ply;*.ter;*.cob;*.scn;*.smd;*.vta;*.xgl;"
    "*.amf;*.assbin;*.b3d;*.iqm;*.ndo;*.q3d;*.sib;*.x3d;*.x3db;*.x3dz;*.x3dbz;"
    "*.pmd;*.pmx|"
    "All Files |*.*|"
    "3MF (3mf)|*.3mf|"
    "glTF (glTF)|*.glTF|"
    "IGES (igs; iges)|*.igs;*.iges|"
    "Collada (dae)|*.dae|"
    "Wavefront Object (obj)|*.obj|"
    "STEP (stp; step)|*.stp;*.step|"
    "STL (stl)|*.stl|"
    "VRML (vrml; wrl)|*.vrml;*.wrl|"
    "3D GameStudio (mdl; hmp)|*.mdl;*.hmp|"
    "3D Studio Max (3ds; ase)|*.3ds;*.ase|"
    "AC3D (ac; ac3d)|*.ac;*.ac3d|"
    "Autodesk/AutoCAD DXF (dxf)|*.dxf|"
    "Biovision BVH (bvh)|*.bvh|"
    "Blender BVH (blend)|*.blend|"
    "CharacterStudio Motion (csm)|*.csm|"
    "DirectX X (x)|*.x|"
    "Doom 3 (md5mesh; md5anim; md5camera)|*.md5mesh;*.md5anim;*.md5camera|"
    "FBX-Format (fbx)|*.fbx|"
    "IFC-STEP (ifc)|*.ifc|"
    "Irrlicht Mesh/Scene (irr; irrmesh)|*.irr;*.irrmesh|"
    "LightWave Model/Scene (lwo; lws)|*.lwo;*.lws|"
    "Milkshape 3D (ms3d)|*.ms3d|"
    "Modo Model (lxo)|*.lxo|"
    "Neutral File Format (nff)|*.nff|"
    "Object File Format (off)|*.off|"
    "Ogre (mesh.xml; skeleton.xml)|*.mesh.xml;*.skeleton.xml|"
    "OpenGEX-Fomat (ogex)|*.ogex|"
    "Quake I/II/III/3BSP (mdl; md2; md3; pk3)|*.mdl;*.md2;*.md3;*.pk3|"
    "Quick3D (q3o; q3s)|*.q3o;*.q3s|"
    "Raw Triangles (raw)|*.raw|"
    "RtCW (mdc)|*.mdc|"
    "Sense8 WorldToolkit (nff)|*.nff|"
    "Polygon File Format (ply)|*.ply|"
    "Stanford Triangle Format (ply)|*.ply|"
    "Terragen Terrain (ter)|*.ter|"
    "TrueSpace (cob; scn)|*.cob;*.scn|"
    "Valve Model (smd; vta)|*.smd;*.vta|"
    "XGL-3D-Format (xgl)|*.xgl|"
    "Additive Manufacturing (amf)|*.amf|"
    "ASSBIN (assbin)|*.assbin|"
    "OpenBVE 3D (b3d)|*.b3d|"
    "Inter-Quake Model (iqm)|*.iqm|"
    "3D Low-polygon Modeler (ndo)|*.ndo|"
    "Quest3D (q3d)|*.q3d|"
    "Silo Model Format (sib)|*.sib|"
    "Extensible 3D (x3d; x3db; x3dz; x3dbz)|*.x3d;*.x3db;*.x3dz;*.x3dbz|"
    "MikuMikuDance Format (pmd; pmx)|*.pmd;*.pmx"
)
