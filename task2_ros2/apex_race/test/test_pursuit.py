import math

import pytest

from apex_race import pursuit as pp


def test_curvature_formula():
    assert pp.curvature(0.1, 0.5) == pytest.approx(2 * 0.1 / 0.25)
    assert pp.curvature(-0.1, 0.5) == pytest.approx(-0.8)
    assert pp.curvature(0.0, 0.5) == 0.0


def test_curvature_matches_circle():
    # A point on a circle of radius R through the robot, tangent to its
    # heading, gives curvature 1 / R.
    R = 2.0
    a = 0.4
    fx, fy = R * math.sin(a), R * (1 - math.cos(a))
    L = math.hypot(fx, fy)
    assert pp.curvature(fy, L) == pytest.approx(1 / R)


def test_curvature_rejects_zero_lookahead():
    with pytest.raises(ValueError):
        pp.curvature(0.1, 0.0)


def test_speed_drops_as_curvature_rises():
    speeds = [pp.speed_for_curvature(k, 0.22, 0.08, 0.6) for k in (0, 0.5, 1, 2, 4)]
    assert speeds[0] == pytest.approx(0.22)
    assert all(a > b for a, b in zip(speeds, speeds[1:]))
    assert pp.speed_for_curvature(100, 0.22, 0.08, 0.6) == 0.08
    assert pp.speed_for_curvature(-1, 0.22, 0.08, 0.6) == pp.speed_for_curvature(1, 0.22, 0.08, 0.6)


def test_to_robot_frame():
    f, l = pp.to_robot_frame(1.0, 1.0, 1.0, 0.0, math.pi / 2)
    assert f == pytest.approx(1.0)
    assert l == pytest.approx(0.0, abs=1e-12)


def test_straight_line_gives_straight_command():
    wps = [(0.1 * i, 0.0) for i in range(50)]
    v, w, k, _ = pp.pursuit_command(wps, 0.0, 0.0, 0.0, 0, 0.5, 0.22, 0.08, 0.6, 1.5)
    assert v == pytest.approx(0.22)
    assert w == pytest.approx(0.0)


def test_target_to_the_left_turns_left():
    wps = [(0.1 * i, 0.3) for i in range(50)]
    v, w, k, _ = pp.pursuit_command(wps, 0.0, 0.0, 0.0, 0, 0.5, 0.22, 0.08, 0.6, 1.5)
    assert k > 0 and w > 0
    assert v < 0.22


def test_nearest_index_window():
    wps = [(float(i), 0.0) for i in range(10)]
    assert pp.nearest_index(wps, 7.2, 0.0) == 7
    assert pp.nearest_index(wps, 7.2, 0.0, start=0, window=3) == 2


def test_wrap_angle():
    assert pp.wrap_angle(3 * math.pi) == pytest.approx(math.pi)
    assert pp.wrap_angle(-0.5) == pytest.approx(-0.5)
