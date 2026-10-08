"""Pure pursuit and speed control. No ROS imports."""

import math


def wrap_angle(a):
    return math.atan2(math.sin(a), math.cos(a))


def to_robot_frame(px, py, x, y, yaw):
    """Express world point (px, py) in the frame of a robot at (x, y, yaw).

    Returns (forward, left).
    """
    dx = px - x
    dy = py - y
    c = math.cos(yaw)
    s = math.sin(yaw)
    return c * dx + s * dy, -s * dx + c * dy


def nearest_index(waypoints, x, y, start=None, window=None):
    """Index of the waypoint nearest to (x, y).

    With start and window set, only search window points ahead of start,
    so the racer never jumps to the far side of the circuit.
    """
    n = len(waypoints)
    if start is None or window is None:
        indices = range(n)
    else:
        indices = ((start + k) % n for k in range(window))
    best = None
    best_d = float("inf")
    for i in indices:
        wx, wy = waypoints[i]
        d = (wx - x) ** 2 + (wy - y) ** 2
        if d < best_d:
            best_d = d
            best = i
    return best


def lookahead_index(waypoints, x, y, start, lookahead):
    """First waypoint from start onward that is at least lookahead away."""
    n = len(waypoints)
    for k in range(n):
        i = (start + k) % n
        wx, wy = waypoints[i]
        if math.hypot(wx - x, wy - y) >= lookahead:
            return i
    return start


def curvature(lateral, lookahead):
    """Pure pursuit curvature: 2 * y / L^2.

    lateral is the left offset y of the lookahead point in the robot frame.
    lookahead is the distance L to that point.
    """
    if lookahead <= 0:
        raise ValueError("lookahead must be positive")
    return 2.0 * lateral / (lookahead ** 2)


def speed_for_curvature(kappa, v_max, v_min, gain):
    """Speed drops as curvature rises: v = v_max / (1 + gain * |kappa|)."""
    v = v_max / (1.0 + gain * abs(kappa))
    return max(v_min, min(v_max, v))


def pursuit_command(waypoints, x, y, yaw, start, lookahead, v_max, v_min, gain, w_max):
    """One pure pursuit step.

    Returns (v, w, kappa, target_index).
    """
    i = lookahead_index(waypoints, x, y, start, lookahead)
    px, py = waypoints[i]
    forward, left = to_robot_frame(px, py, x, y, yaw)
    dist = math.hypot(forward, left)
    if dist < 1e-6:
        return 0.0, 0.0, 0.0, i
    kappa = curvature(left, dist)
    v = speed_for_curvature(kappa, v_max, v_min, gain)
    if forward < 0:
        # Target is behind: turn on the spot toward it.
        v = 0.0
        w = math.copysign(w_max, left)
        return v, w, kappa, i
    w = max(-w_max, min(w_max, v * kappa))
    return v, w, kappa, i
