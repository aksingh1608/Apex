"""Lap timing from finish line crossings. No ROS imports."""


def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def segments_intersect(p1, p2, q1, q2):
    """True if segment p1-p2 crosses segment q1-q2 (touching counts)."""
    def orient(a, b, c):
        v = _cross(b[0] - a[0], b[1] - a[1], c[0] - a[0], c[1] - a[1])
        if abs(v) < 1e-12:
            return 0
        return 1 if v > 0 else -1

    def on_segment(a, b, c):
        return (min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12 and
                min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12)

    o1 = orient(p1, p2, q1)
    o2 = orient(p1, p2, q2)
    o3 = orient(q1, q2, p1)
    o4 = orient(q1, q2, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_segment(p1, p2, q1):
        return True
    if o2 == 0 and on_segment(p1, p2, q2):
        return True
    if o3 == 0 and on_segment(q1, q2, p1):
        return True
    if o4 == 0 and on_segment(q1, q2, p2):
        return True
    return False


def crossing_direction(prev, curr, line_a, line_b):
    """Which way the move prev -> curr crosses the line a -> b.

    Returns +1 if the move goes from the right of a->b to its left,
    -1 for the other way, and 0 if the move does not cross the line.
    """
    if not segments_intersect(prev, curr, line_a, line_b):
        return 0
    lx = line_b[0] - line_a[0]
    ly = line_b[1] - line_a[1]
    s_prev = _cross(lx, ly, prev[0] - line_a[0], prev[1] - line_a[1])
    s_curr = _cross(lx, ly, curr[0] - line_a[0], curr[1] - line_a[1])
    if s_prev < 0 <= s_curr:
        return 1
    if s_prev > 0 >= s_curr:
        return -1
    return 0


class LapTimer:
    """Counts laps from finish line crossings.

    The first forward crossing starts lap 1. Each later forward crossing
    ends a lap. Crossings closer together than min_lap_time are ignored,
    so jitter on the line cannot count twice.

    forward_sign is the crossing_direction value that counts as forward.
    """

    def __init__(self, line_a, line_b, forward_sign=1, min_lap_time=5.0):
        self.line_a = line_a
        self.line_b = line_b
        self.forward_sign = forward_sign
        self.min_lap_time = min_lap_time
        self.last_cross_time = None
        self.lap_times = []
        self.prev = None

    @property
    def started(self):
        return self.last_cross_time is not None

    @property
    def laps_done(self):
        return len(self.lap_times)

    def update(self, x, y, t):
        """Feed one pose. Returns "start", "lap" or None."""
        curr = (x, y)
        prev = self.prev
        self.prev = curr
        if prev is None:
            return None
        d = crossing_direction(prev, curr, self.line_a, self.line_b)
        if d != self.forward_sign:
            return None
        if self.last_cross_time is None:
            self.last_cross_time = t
            return "start"
        if t - self.last_cross_time < self.min_lap_time:
            return None
        self.lap_times.append(t - self.last_cross_time)
        self.last_cross_time = t
        return "lap"

    def reset(self):
        self.last_cross_time = None
        self.lap_times = []
        self.prev = None
