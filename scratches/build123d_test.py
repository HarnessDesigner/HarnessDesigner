# ******************* WORKING CODE!!! *********************
# I will be using this with OpenGL to handle the rendering of the transitions.


import math
from build123d import *

branches = [
            {
                "min": 6.3,
                "max": 26.0,
                "length": 54.0,
                "bulb_length": 30.0,
                "bulb_offset": "[7.0, 0.0]",
                "angle": -180.0,
                "flange_height": 3.0,
                "flange_width": 5.0
            },
            {
                "min": 5.5,
                "max": 16.0,
                "length": 36.0,
                "bulb_length": 21.0,
                "angle": 0.0
            },
            {
                "min": 5.5,
                "max": 16.0,
                "length": 35.0,
                "bulb_length": 17.0,
                "angle": 90.0
            }
        ]

model = None

z_pos = 0

for branch in branches:
    min_dia = branch['min']
    max_dia = branch['max']
    length = branch['length']
    bulb_len = branch['bulb_length']
    angle = branch['angle']
    z_pos = max(max_dia, z_pos)

    plane = Plane(origin=(0, 0, 0), z_dir=(1, 0, 0))

    if bulb_len:
        if 'bulb_offset' in branch:
            bulb_offset = eval(branch['bulb_offset'])
            p = Plane(origin=(bulb_offset[0], 0, 0), z_dir=(1, 0, 0)).rotated((0, 0, angle))
        else:
            p = plane.rotated((0, 0, angle))

        if model is None:
            model = p * extrude(Circle(max_dia / 2), bulb_len)
        else:
            model += p * extrude(Circle(max_dia / 2), bulb_len)

        if 'bulb_offset' in branch:
            p = Plane(origin=(bulb_offset[0], 0, 0), z_dir=(1, 0, 0))
            model += p * Sphere(max_dia / 2)  # .rotate(Axis(origin=(0, 0, 0), direction=(0, -1, 0)), 90.0)
            p = Plane(origin=(bulb_offset[0] - bulb_len, 0, 0), z_dir=(1, 0, 0))
            model += p * Sphere(max_dia / 2)  # .rotate(Axis(origin=(0, 0, 0), direction=(0, -1, 0)), 90.0)
        else:
            r = math.radians(angle)
            x = bulb_len * math.cos(r)
            y = bulb_len * math.sin(r)

            p = Plane(origin=(x, y, 0), z_dir=(1, 0, 0))
            model += p * Sphere(max_dia / 2).rotate(Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle)

    p = plane.rotated((0, 0, angle))
    model += p * extrude(Circle(min_dia / 2), length)

    if 'flange_width' in branch:
        fw = branch['flange_width']
        fh = branch['flange_height']

        p = Plane(origin=(-(length - fw), 0), z_dir=(1, 0, 0)).rotated((0, 0, angle))
        model += p * extrude(Circle(min_dia / 2 + fh), fw)


export_stl(model, "test_stl.stl")

print('DONE!')
