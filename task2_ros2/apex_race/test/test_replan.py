import math

import pytest

from apex_race import replan as rp


def make_scan(fn, n=360):
    inc = 2 * math.pi / n
    return [fn(i * inc) for i in range(n)], 0.0, inc


def test_corridor_sees_object_ahead_only():
    pts = [(0.4, 0.05), (0.3, 0.5), (-0.2, 0.0)]
    assert rp.corridor_distance(pts, 0.2, 1.0) == pytest.approx(0.4)
    assert rp.corridor_distance([(0.3, 0.5)], 0.2, 1.0) == 1.0


def test_free_space_picks_open_side():
    # Wall close on the right (negative angles), open on the left.
    def fn(a):
        a = math.atan2(math.sin(a), math.cos(a))
        return 0.4 if a < 0 else 3.0
    ranges, amin, inc = make_scan(fn)
    left = rp.free_space(ranges, amin, inc, math.radians(15), math.radians(75), 0.12, 3.5, 2.0)
    right = rp.free_space(ranges, amin, inc, math.radians(-75), math.radians(-15), 0.12, 3.5, 2.0)
    assert left > right
    assert rp.choose_side(left, right) == 1
    assert rp.choose_side(0.3, 0.9) == -1


def test_inf_counts_as_free():
    ranges, amin, inc = make_scan(lambda a: float("inf"))
    assert rp.free_space(ranges, amin, inc, 0.2, 1.0, 0.12, 3.5, 2.0) == pytest.approx(2.0)


def test_front_and_min_range():
    def fn(a):
        a = math.atan2(math.sin(a), math.cos(a))
        return 0.5 if abs(a) < math.radians(5) else (0.05 if a > 3 else 2.0)
    ranges, amin, inc = make_scan(fn)
    assert rp.front_range(ranges, amin, inc, math.radians(20), 0.12, 3.5) == 0.5
    # 0.05 is below range_min, so it is not valid
    assert rp.min_range(ranges, 0.12, 3.5) == 0.5


def test_shift_moves_left_of_travel():
    wps = [(0.1 * i, 0.0) for i in range(40)]
    out = rp.shift_waypoints(wps, 10, 10, 0.3, 3)
    assert out[:10] == wps[:10]
    assert out[20:] == wps[20:]
    assert out[15][1] == pytest.approx(0.3)
    assert out[10][1] == pytest.approx(0.1)
    assert all(abs(out[i][0] - wps[i][0]) < 1e-9 for i in range(40))


def test_shift_right_and_wraps():
    wps = [(math.cos(a), math.sin(a)) for a in [2 * math.pi * i / 36 for i in range(36)]]
    out = rp.shift_waypoints(wps, 34, 6, -0.2, 1)
    # Counterclockwise circle: right of travel is outward.
    for i in (34, 35, 0, 1, 2, 3):
        assert math.hypot(*out[i]) > 1.0
    assert out[10] == wps[10]


def test_contact_counter_hysteresis():
    c = rp.ContactCounter(0.15, 0.20)
    seq = [0.5, 0.14, 0.13, 0.18, 0.14, 0.25, 0.1]
    starts = [c.update(r) for r in seq]
    assert starts == [False, True, False, False, False, False, True]
    assert c.count == 2


def walls_and(extra):
    pts = [(x / 20, 0.6) for x in range(1, 30)] + [(x / 20, -0.6) for x in range(1, 30)]
    return pts + extra


def test_free_beside_cone_right_of_centre():
    cone = [(0.6, -0.05), (0.59, -0.1), (0.6, -0.15)]
    left, right, lo, hi = rp.free_beside(walls_and(cone), 1.0, 0.17, 1.0)
    assert hi == pytest.approx(-0.05)
    assert lo == pytest.approx(-0.15)
    assert left == pytest.approx(0.65)
    assert right == pytest.approx(0.45)
    assert rp.choose_side(left, right) == 1


def test_free_beside_car_on_centre_line_is_not_zero():
    # The old smallest-gap measure gave 0.00 m on both sides here.
    car = [(0.6, y / 100) for y in range(-5, 6)]
    left, right, lo, hi = rp.free_beside(walls_and(car), 1.0, 0.17, 1.0)
    assert left == pytest.approx(0.55)
    assert right == pytest.approx(0.55)


def test_free_beside_grows_past_the_corridor():
    wide = [(0.6, y / 100) for y in range(-10, 31, 3)]
    left, right, lo, hi = rp.free_beside(walls_and(wide), 1.0, 0.17, 1.0)
    assert hi == pytest.approx(0.29)
    assert left == pytest.approx(0.31)


def test_free_beside_empty_corridor():
    assert rp.free_beside(walls_and([]), 1.0, 0.17, 1.0)[:2] == (1.0, 1.0)


def test_pass_offset():
    assert rp.pass_offset(1, -0.15, -0.05, 0.25, 0.3, 0.38) == pytest.approx(0.3)
    assert rp.pass_offset(-1, -0.05, 0.05, 0.25, 0.3, 0.38) == pytest.approx(-0.3)
    assert rp.pass_offset(-1, -0.2, 0.05, 0.25, 0.3, 0.38) == pytest.approx(-0.38)
