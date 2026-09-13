# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ....geometry import point as _point
from .... import check_types as _check_types
from ... import mixins as _wire_type_base


if TYPE_CHECKING:
    from ....gl import canvas_3d as _canvas3d


class WireTypeMixin(_wire_type_base.WireTypeMixin):
    """3D-editor specialization of the shared
    ``objects.mixins.wire.WireTypeMixin`` -- see that module's own
    docstring for the full rationale. Supplies this view's own
    ``_waypoints``/``_point_on_wire``; ``_segments``/``get_closest_point``/
    ``get_closest_endpoint`` are inherited unchanged.
    """
    editor3d: "_canvas3d.Canvas3D" = None

    @staticmethod
    @_check_types.do
    def _waypoints(db_obj):
        """This mixin is also shared by objects.objects_3d.bundle.Bundle
        (see get_closest_endpoint's callers in handlers.
        bundle_layout_handler) -- PJTBundle has no waypoints3d of its own
        (bundles haven't been given the same single-row/tagged-waypoint
        treatment PJTWire has), so it's read via getattr rather than
        assumed present; a bundle simply has zero interior waypoints
        today, same as it always has.
        """
        return getattr(db_obj, 'waypoints3d', ())

    @staticmethod
    @_check_types.do
    def _closest_point_on_segment_to_ray(seg_p1, seg_p2, ray_origin, ray_dir):
        """
        Find the closest point on line segment (seg_p1, seg_p2) to a ray.

        Uses the parametric formula for closest points between two 3D lines,
        then clamps the result to the line segment.
        """

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

    @_check_types.do
    def _point_on_wire(
        self,
        mouse_pos: _point.Point
    ) -> tuple[np.ndarray, int] | tuple[None, None]:

        """
        Project a mouse ray onto the closest point along the wire's whole
        path -- every sub-segment from start through each interior
        waypoint to stop is tried, and whichever one the ray actually
        passes closest to wins (perpendicular ray-to-point distance, not
        just the clamped parametric position along that one segment).

        The winning segment's index is returned too -- since segment i
        sits between interior waypoint i-1 and waypoint i (0-based, see
        _segments()), that's already exactly the insertion index a caller
        needs to add a new waypoint there (shift every waypoint from that
        index onward up by one, tag the new point at the freed index) --
        finding it doesn't require a second, separate walk over the
        wire's segments the way computing it from the resolved point
        afterward would (see handlers.wire_layout_handler's old
        _find_insertion_index, now unused for this reason).

        :param mouse_pos: Mouse position in viewport coordinates.
        :type mouse_pos: _point.Point
        :returns: (closest_point, winning_segment_index), or
            ``(None, None)`` when the ray cannot be constructed.
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

        camera = self.editor3d.camera

        # Radius the wire actually renders at -- the physical tolerance
        # for "the ray touches this segment's surface at all". Needed
        # because perpendicular ray-to-segment distance alone can't tell
        # two of a *bent* wire's own segments apart where they visually
        # cross on screen (impossible on the old always-one-straight-
        # segment model, real now): both can have near-zero perpendicular
        # distance at the crossing point, and picking whichever is merely
        # smaller ignores which one the camera would actually see -- see
        # camera.closest_point below, which resolves that the same way
        # gl.object_picker.find_object resolves whole-object ray hits.
        radius_sq = (float(self._scale.x) / 2.0) ** 2

        # (segment_index, candidate_point) for every segment the ray
        # actually touches within the wire's own radius.
        candidates_by_segment = []

        for i, (seg_p1, seg_p2) in enumerate(self._segments()):
            candidate = self._closest_point_on_segment_to_ray(
                seg_p1, seg_p2, ray_origin, ray_direction)

            # Squared -- only the threshold comparison matters here, never
            # the real distance value, and square root is monotonic (a < b
            # iff sqrt(a) < sqrt(b) for non-negative a, b), so comparing
            # squared distance against a squared threshold gives the
            # identical result without ever paying for a sqrt call.
            perp_vec = np.cross(candidate - ray_origin, ray_direction)
            perp_dist_sq = float(np.dot(perp_vec, perp_vec))
            if perp_dist_sq <= radius_sq:
                candidates_by_segment.append((i, candidate))

        if candidates_by_segment:
            points = [c[1] for c in candidates_by_segment]
            winner, best_point = camera.closest_point(points)
            best_idx = candidates_by_segment[winner][0]
        else:
            best_point = best_idx = None

        if best_point is None:
            # Nothing was within the wire's own radius (e.g. a click just
            # off the tube's surface, still meant for this wire) -- fall
            # back to whichever segment the ray simply passes closest to
            # overall; depth doesn't matter here since nothing actually
            # qualified as "on" the wire in the first place.
            best_dist_sq = None
            for i, (seg_p1, seg_p2) in enumerate(self._segments()):
                candidate = self._closest_point_on_segment_to_ray(
                    seg_p1, seg_p2, ray_origin, ray_direction)
                perp_vec = np.cross(candidate - ray_origin, ray_direction)
                dist_sq = float(np.dot(perp_vec, perp_vec))
                if best_dist_sq is None or dist_sq < best_dist_sq:
                    best_dist_sq = dist_sq
                    best_point = candidate
                    best_idx = i

        if best_point is None:
            # Fallback to wire midpoint (segment 0 -- the only one on a
            # wire with no interior waypoints, still the common case)
            p1 = self.start_position.as_numpy
            p2 = self.stop_position.as_numpy
            best_point = (p1 + p2) / 2.0
            best_idx = 0

        return best_point, best_idx
