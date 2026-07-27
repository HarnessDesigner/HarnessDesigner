# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Shape helper modules used to build reusable geometry and 2D overlays.

This subpackage collects small generators and painter-backed helpers used by
other parts of :mod:`harness_designer`.
"""


_arrow_vbo = None
_box_vbo = None
_circle_vbo = None
_cylinder_vbo = None
_cylinder_helix_vbo = None
_helix_vbo = None
_rectangle_vbo = None
_sphere_vbo = None


def cache_primitives(mainframe):
    from . import arrow
    from . import box
    from . import circle
    from . import cylinder
    from . import cylinder_helix
    from . import helix
    from . import rectangle
    from . import sphere

    global _arrow_vbo
    global _box_vbo
    global _circle_vbo
    global _cylinder_vbo
    global _cylinder_helix_vbo
    global _helix_vbo
    global _rectangle_vbo
    global _sphere_vbo

    with mainframe.editor3d.context:
        _arrow_vbo = arrow.create_vbo()
        _box_vbo = box.create_vbo()
        _cylinder_vbo = cylinder.create_vbo()
        _cylinder_helix_vbo = cylinder_helix.create_vbo()
        _sphere_vbo = sphere.create_vbo()
        _helix_vbo = helix.create_vbo(1)

    with mainframe.editor2d.context:
        _rectangle_vbo = rectangle.create_vbo()
        _circle_vbo = circle.create_vbo()
