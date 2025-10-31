from PIL import Image, ImageFilter
import numpy as np
import math

img = Image.open(r'C:\Users\drsch\PycharmProjects\harness_designer\harness_designer\image\connectors\X120-M_pin_mask.png').convert('RGBA')


width, height = img.size
rects = []

SHAPE_RECT = 1
SHAPE_CIRCLE = 2

img2 = Image.new('RGBA', (width, height))


def get_angle(coord1, coord2):
    p1, p2 = coord1
    p3, p4 = coord2

    r = math.atan2(p4 - p2, p3 - p1)
    angle = math.degrees(r)

    if angle < 0:
        angle += 360

    return angle


def get_rotation_matrix(angle) -> np.array:
    x_angle = np.radians(0.0)
    y_angle = np.radians(0.0)
    z_angle = np.radians(angle)

    Rx = np.array([[1, 0, 0],
                   [0, np.cos(x_angle), -np.sin(x_angle)],
                   [0, np.sin(x_angle), np.cos(x_angle)]])

    Ry = np.array([[np.cos(y_angle), 0, np.sin(y_angle)],
                   [0, 1, 0],
                   [-np.sin(y_angle), 0, np.cos(y_angle)]])

    Rz = np.array([[np.cos(z_angle), -np.sin(z_angle), 0],
                   [np.sin(z_angle), np.cos(z_angle), 0],
                   [0, 0, 1]])

    return Rz @ Ry @ Rx


R180 = get_rotation_matrix(180.0)


class Circle:
    def __init__(self, x1, y1, x2, y2):
        self.x = abs(((x2 - x1) / 2.0))
        self.y = abs(((y2 - y1) / 2.0))

        if x1 <= x2:
            self.x += x1
        else:
            self.x += x2

        if y1 <= y2:
            self.y += y1
        else:
            self.y += y2

        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.diameter = abs(x2 - x1)
        self.radius = abs(((x2 - x1) / 2.0))

    def __str__(self):
        return (f'Circle(x={self.x}, y={self.y}, x1={self.x1}, y1={self.y1}, '
                f'x2={self.x2}, y2={self.y2}, radius={self.radius}, '
                f'dia={self.diameter})')


class Rect:

    def __init__(self, x1, y1, x2, y2, width, height, angle):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

        self.width = width
        self.height = height
        self.angle = angle

    def __str__(self):
        return f'Rect(x1={self.x1}, y1={self.y1}, x1={self.x2}, y2={self.y2}, width={self.width}, height={self.height}, angle={self.angle})'


class Shape:

    def __init__(self, x1, y1):
        self._x1 = x1
        self._y1 = y1
        self._x2 = None
        self._y2 = None
        self.pixels = [[x1, y1]]
        self.shape = SHAPE_RECT

    def hit_test(self, x, y):
        for x1, y1 in self.pixels:
            for off_x, off_y in (
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ):
                if x1 + off_x == x and y1 + off_y == y:
                    self.pixels.append([x, y])
                    return True
        try:
            v = img.getpixel((x + 1, y))
            if v:
                for x1, y1 in self.pixels:
                    for off_x, off_y in (
                        (1, 0),
                        (-1, 0),
                        (0, 1),
                        (0, -1),
                        (-1, -1),
                        (-1, 1),
                        (1, -1),
                        (1, 1),
                    ):
                        if x1 + off_x == x + 1 and y1 + off_y == y:
                            self.pixels.append([x, y])
                            return True
        except:
            pass

        return False

    def process(self):
        pixels = [p + [0] for p in self.pixels]
        pixels = np.array(pixels, dtype=float)

        xs = pixels[:, 0]
        ys = pixels[:, 1]
        x1 = min(xs.tolist())
        y1 = min(ys.tolist())
        x2 = max(xs.tolist())
        y2 = max(ys.tolist())

        center_x = x1 + ((x2 - x1) / 2.0)
        center_y = y1 + ((y2 - y1) / 2.0)

        max_xs = None
        max_ys = None

        min_xs = None
        min_ys = None

        for p in self.pixels:
            if p[0] == x2:
                if max_xs is None:
                    max_xs = p
                elif max_xs[1] < p[1]:
                    max_xs = p
            if p[1] == y2:
                if max_ys is None:
                    max_ys = p
                elif max_ys[0] < p[0]:
                    max_ys = p

            if p[0] == x1:
                if min_xs is None:
                    min_xs = p
                elif min_xs[1] < p[1]:
                    min_xs = p
            if p[1] == y1:
                if min_ys is None:
                    min_ys = p
                elif min_ys[0] < p[0]:
                    min_ys = p

        if max_xs is None or max_ys is None:
            raise RuntimeError

        if max_xs != max_ys:
            p1x, p1y = max_xs
            p2x, p2y = max_ys

            r_side_x = (p1x + p2x) / 2.0
            r_side_y = (p1y + p2y) / 2.0
        else:
            r_side_x = x2
            r_side_y = (y1 + y2) / 2.0

        center = np.array([center_x, center_y, 0.0], dtype=float)

        angle = get_angle((center_x, center_y), (r_side_x, r_side_y))

        R = get_rotation_matrix(angle - 359)
        arr = np.array([min_xs + [0.0], min_ys + [0.0], max_xs + [0.0], max_ys + [0.0]], dtype=float)
        arr -= center
        arr @= R
        arr += center

        tl = (min(arr[:, 0]), min(arr[:, 1]))
        br = (max(arr[:, 0]), max(arr[:, 1]))

        width = br[0] - tl[0] + 1
        height = br[1] - tl[1] + 1

        R = get_rotation_matrix(angle - 45.0)

        rpixels = [p + [0] for p in self.pixels]
        rpixels = np.array(rpixels, dtype=float)
        rpixels -= center
        rpixels @= R
        rpixels += center

        if angle != 0.0:
            R = get_rotation_matrix(angle)
            arr = np.array([tl + (0.0,), br + (0.0,)], dtype=float)
            arr -= center
            arr @= R
            arr += center

            tl, br = [tuple(itm.tolist()[:-1]) for itm in arr]
        else:
            tl, br = ((x1, y1), (x2, y2))

        rpixels = rpixels.tolist()
        pixels = pixels.tolist()

        for p in rpixels:
            if p not in pixels:
                return Rect(*(tl + br + (width, height, angle)))
        # tuple(self.pixels[0]) + tuple(self.pixels[-1])
        return Circle(*(tl + br))


img = img.convert('RGB')
img = img.convert("L")
img = img.filter(ImageFilter.FIND_EDGES)

vals = set()
for y in range(height):
    for x in range(width):
        val = img.getpixel((x, y))
        if val:
            for rect in rects:
                if rect.hit_test(x, y):
                    break
            else:
                rects.append(Shape(x, y))


shapes = [rect.process() for rect in rects]

for item in shapes:
    print(item)

img2.show()
