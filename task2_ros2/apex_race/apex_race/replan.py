"""LiDAR helpers and the REPLAN waypoint shift. No ROS imports.

Scan angles follow ROS: 0 rad points forward, positive angles turn left.
"""

import math


def valid(r, range_min, range_max):
    return math.isfinite(r) and range_min <= r <= range_max


def scan_points(ranges, angle_min, angle_increment, range_min, range_max):
    """Turn a scan into (forward, left) points in the sensor frame."""
    pts = []
    for i, r in enumerate(ranges):
        if not valid(r, range_min, range_max):
            continue
        a = angle_min + i * angle_increment
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def corridor_distance(points, half_width, max_dist):
    """Distance to the nearest point inside the straight corridor ahead.

    The corridor runs forward from the sensor and is 2 * half_width wide.
    Returns max_dist if the corridor is empty.
    """
    best = max_dist
    for fx, fy in points:
        if 0.0 < fx < best and abs(fy) <= half_width:
            best = fx
    return best


def sector_ranges(ranges, angle_min, angle_increment, lo, hi, range_min, range_max, cap):
    """Ranges with angle in [lo, hi]. Missing or far returns count as cap."""
    out = []
    for i, r in enumerate(ranges):
        a = math.atan2(math.sin(angle_min + i * angle_increment),
                       math.cos(angle_min + i * angle_increment))
        if lo <= a <= hi:
            if valid(r, range_min, range_max):
                out.append(min(r, cap))
            else:
                out.append(cap)
    return out


def min_range(ranges, range_min, range_max):
    vals = [r for r in ranges if valid(r, range_min, range_max)]
    return min(vals) if vals else float("inf")


def front_range(ranges, angle_min, angle_increment, half_angle, range_min, range_max):
    """Lowest valid range within +-half_angle of straight ahead."""
    vals = sector_ranges(ranges, angle_min, angle_increment, -half_angle, half_angle,
                         range_min, range_max, float("inf"))
    vals = [v for v in vals if math.isfinite(v)]
    return min(vals) if vals else float("inf")


def free_space(ranges, angle_min, angle_increment, lo, hi, range_min, range_max, cap):
    """Mean range in a sector, with far or missing returns counted as cap."""
    vals = sector_ranges(ranges, angle_min, angle_increment, lo, hi, range_min, range_max, cap)
    return sum(vals) / len(vals) if vals else 0.0


def lateral_gap(points, ahead, cap):
    """Free space on each side of the path ahead, from scan points.

    Looks at points with 0 < forward < ahead. The left gap is the smallest
    left offset of any point on the left, the right gap the same on the
    right. A side with no points gets cap. Returns (left_gap, right_gap).
    """
    left = cap
    right = cap
    for fx, fy in points:
        if not 0.0 < fx < ahead:
            continue
        if fy >= 0:
            left = min(left, fy)
        else:
            right = min(right, -fy)
    return left, right


def choose_side(left_free, right_free):
    """+1 to pass on the left, -1 to pass on the right. Ties go left."""
    return 1 if left_free >= right_free else -1


def shift_waypoints(waypoints, start, count, offset, ramp):
    """Shift count waypoints from start sideways by offset (positive = left).

    Left is relative to the direction of travel along the list. The shift
    ramps up over the first ramp points and down over the last ramp points,
    so the new path has no sharp kink. Returns a new list.
    """
    n = len(waypoints)
    out = list(waypoints)
    if count <= 0 or offset == 0:
        return out
    count = min(count, n)
    ramp = max(1, min(ramp, count // 2))
    for k in range(count):
        i = (start + k) % n
        px, py = waypoints[(i - 1) % n]
        qx, qy = waypoints[(i + 1) % n]
        tx, ty = qx - px, qy - py
        norm = math.hypot(tx, ty)
        if norm < 1e-9:
            continue
        nx, ny = -ty / norm, tx / norm
        if k < ramp:
            scale = (k + 1) / ramp
        elif k >= count - ramp:
            scale = (count - k) / ramp
        else:
            scale = 1.0
        x, y = waypoints[i]
        out[i] = (x + nx * offset * scale, y + ny * offset * scale)
    return out


class ContactCounter:
    """Counts contact events from the lowest LiDAR range.

    A contact starts when the range drops below enter and ends when it
    rises above exit. Each contact counts once.
    """

    def __init__(self, enter, exit_):
        self.enter = enter
        self.exit = exit_
        self.in_contact = False
        self.count = 0

    def update(self, r):
        """Feed one lowest range. Returns True when a new contact starts."""
        if not self.in_contact and r < self.enter:
            self.in_contact = True
            self.count += 1
            return True
        if self.in_contact and r > self.exit:
            self.in_contact = False
        return False
