# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ....geometry import point as _point
from ....geometry import angle as _angle


if TYPE_CHECKING:
    from ....gl import canvas3d as _canvas3d


class WireTypeMixin:
    start_position: _point.Point = None
    stop_position: _point.Point = None
    editor3d: "_canvas3d.Canvas3D" = None
    db_obj = None

    def _closest_point_on_segment_to_ray(self, ray_origin, ray_dir):
        """
        Find the closest point on line segment (seg_p1, seg_p2) to a ray.

        Uses the parametric formula for closest points between two 3D lines,
        then clamps the result to the line segment.
        """

        seg_p1 = self.start_position.as_numpy
        seg_p2 = self.stop_position.as_numpy

        # Wire segment direction
        w = seg_p2 - seg_p1
        w_len = np.linalg.norm(w)

        if w_len < 1e-6:
            return seg_p1

        w = w / w_len

        # Vector from ray origin to segment start
        u = seg_p1 - ray_origin

        # Calculate parameters for closest points
        a = np.dot(w, w)  # Should be 1 (normalized)
        b = np.dot(w, ray_dir)
        c = np.dot(ray_dir, ray_dir)  # Should be 1 (normalized)
        d = np.dot(w, u)
        e = np.dot(ray_dir, u)

        denom = a * c - b * b

        if abs(denom) < 1e-6:
            # Lines are parallel, use perpendicular projection
            t = np.dot(u, w)
        else:
            t = (b * e - c * d) / denom

        # Clamp t to [0, wire_length]
        t = np.clip(t, 0.0, w_len)

        # Calculate closest point on segment
        closest = seg_p1 + t * w

        return closest

    def _point_on_wire(
        self,
        mouse_pos: "_point.Point"
    ) -> np.ndarray | tuple[None, None]:

        """
        Project a mouse ray onto the closest point along a wire segment.

        :param mouse_pos: Mouse position in viewport coordinates.
        :type mouse_pos: _point.Point
        :returns: Closest point on the segment, or ``(None, None)`` when the ray
            cannot be constructed.
        :rtype: numpy.ndarray | tuple[None, None]
        """

        # Build ray from mouse position
        viewport = self.editor3d.camera.viewport

        vx, vy, vw, vh = viewport

        x = mouse_pos.x
        y = (vh - mouse_pos.y)

        ndc_x = (2.0 * (x - vx) / vw) - 1.0
        ndc_y = (2.0 * (y - vy) / vh) - 1.0

        # Unproject to get ray
        near_world = self.editor3d.camera.unproject_from_ndc(ndc_x, ndc_y, -1.0)
        far_world = self.editor3d.camera.unproject_from_ndc(ndc_x, ndc_y, 1.0)

        if near_world is None or far_world is None:
            return None, None

        ray_origin = np.array(near_world, dtype=np.float32)
        ray_direction = np.array(far_world, dtype=np.float32) - ray_origin
        ray_direction /= np.linalg.norm(ray_direction)

        # Find closest point on wire line segment to the ray
        # This uses the formula for closest point between two 3D line segments
        closest_point = self._closest_point_on_segment_to_ray(ray_origin,
                                                              ray_direction)

        if closest_point is None:
            # Fallback to wire midpoint
            p1 = self.start_position.as_numpy
            p2 = self.stop_position.as_numpy
            closest_point = (p1 + p2) / 2.0

        return closest_point

    def get_closest_point(
        self,
        mouse_pos: "_point.Point"
    ) -> tuple[_point.Point | None, _angle.Angle | None]:

        """
        Find the closest point on a wire to where the user clicked.

        This computes:
        1. Ray from mouse position
        2. Closest point on wire line segment to that ray
        3. Wire direction at that point

        Returns:
            tuple: (closest_point, wire_angle) or (None, None)
        """

        # Get wire endpoints
        p1 = self.start_position.as_numpy
        p2 = self.stop_position.as_numpy

        closest_point = self._point_on_wire(mouse_pos)

        # Calculate wire direction (from p1 to p2)
        wire_direction = p2 - p1
        wire_length = np.linalg.norm(wire_direction)

        if wire_length < 0.001:
            return None, None

        wire_direction /= wire_length

        # Convert to angle
        wire_angle = _angle.Angle.from_direction(wire_direction)

        return _point.Point(*closest_point), wire_angle

    def get_closest_endpoint(
        self,
        mouse_pos: "_point.Point",
        endpoint_tolerance=5.0
    ):
        """
        Find whether a picked wire location lands on an existing endpoint.

        :param mouse_pos: Mouse position in viewport coordinates.
        :type mouse_pos: _point.Point
        :param endpoint_tolerance: Minimum tolerance used for endpoint snapping.
        :type endpoint_tolerance: float
        :returns: Picked position, whether it matches an endpoint, and the endpoint
            name when applicable.
        :rtype: tuple[object, bool, str | None]
        """

        # Get wire endpoints
        p1 = self.start_position.as_numpy
        p2 = self.stop_position.as_numpy

        closest_point = self._point_on_wire(mouse_pos)

        # Check if closest point is near an existing endpoint
        dist_to_p1 = np.linalg.norm(closest_point - p1)
        dist_to_p2 = np.linalg.norm(closest_point - p2)

        # Use wire diameter as tolerance for endpoint detection
        wire_diameter = self.db_obj.part.od_mm
        tolerance = max(wire_diameter, endpoint_tolerance)

        if dist_to_p1 < tolerance:
            # Placing at start endpoint - return the ACTUAL Point instance
            # This ensures the layout will bind to the same Point callbacks
            return p1, True, 'start'
        elif dist_to_p2 < tolerance:
            # Placing at end endpoint - return the ACTUAL Point instance
            return p2, True, 'stop'
        else:
            # Placing in middle - return coordinates for NEW Point creation
            # The project will create a new Point and share it between layout and wires
            position = _point.Point(*closest_point)

            return position, False, None
