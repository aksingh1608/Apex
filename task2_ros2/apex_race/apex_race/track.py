"""Circuit geometry built from circuit.yaml. No ROS imports.

The track is a stadium: two straights joined by two half circles.
Cars run counterclockwise, so the front straight (y < 0) runs in +x.
"""

import math

import yaml


def load_circuit(path):
    with open(path) as f:
        return yaml.safe_load(f)


def centre_line(straight_length, turn_radius, spacing):
    """Return centre line waypoints as a list of (x, y), counterclockwise.

    The list starts on the front straight at x = -straight_length / 2 and
    does not repeat its first point at the end.
    """
    half = straight_length / 2.0
    r = turn_radius
    points = []

    def straight(x0, y0, x1, y1):
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(1, round(length / spacing))
        for i in range(n):
            t = i / n
            points.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))

    def turn(cx, start_angle):
        n = max(1, round(math.pi * r / spacing))
        for i in range(n):
            a = start_angle + math.pi * i / n
            points.append((cx + r * math.cos(a), r * math.sin(a)))

    straight(-half, -r, half, -r)       # front straight, +x
    turn(half, -math.pi / 2)            # turns one and two
    straight(half, r, -half, r)         # back straight, -x
    turn(-half, math.pi / 2)            # turns three and four
    return points


def circuit_waypoints(circuit):
    t = circuit["track"]
    return centre_line(t["straight_length"], t["turn_radius"], t["waypoint_spacing"])


def finish_line(circuit):
    """Return the finish line segment ((x, y), (x, y)) across the front straight."""
    t = circuit["track"]
    x = circuit["finish_line_x"]
    r = t["turn_radius"]
    w = t["width"] / 2.0
    return (x, -r - w), (x, -r + w)


def path_length(points, closed=True):
    total = 0.0
    n = len(points)
    last = n if closed else n - 1
    for i in range(last):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def distance_to_centre_line(x, y, straight_length, turn_radius):
    """Signed distance from the centre line. Positive means toward the outer wall."""
    half = straight_length / 2.0
    if x > half:
        return math.hypot(x - half, y) - turn_radius
    if x < -half:
        return math.hypot(x + half, y) - turn_radius
    return abs(y) - turn_radius
