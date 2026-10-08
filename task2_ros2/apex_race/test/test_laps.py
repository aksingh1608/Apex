import pytest

from apex_race.laps import LapTimer, crossing_direction, segments_intersect

LINE = ((0.0, -1.8), (0.0, -0.6))


def test_intersect():
    assert segments_intersect((-1, -1), (1, -1), *LINE)
    assert not segments_intersect((-1, 0), (1, 0), *LINE)
    assert not segments_intersect((0.1, -1), (0.5, -1), *LINE)


def test_direction():
    fwd = crossing_direction((-0.05, -1.2), (0.05, -1.2), *LINE)
    back = crossing_direction((0.05, -1.2), (-0.05, -1.2), *LINE)
    assert fwd == -back and fwd != 0


def drive(timer, x0, x1, t):
    timer.update(x0, -1.2, t)
    return timer.update(x1, -1.2, t + 0.1)


def test_lap_timer_counts_laps():
    sign = crossing_direction((-0.05, -1.2), (0.05, -1.2), *LINE)
    timer = LapTimer(*LINE, forward_sign=sign, min_lap_time=5.0)
    assert drive(timer, -0.05, 0.05, 0.0) == "start"
    assert drive(timer, -0.05, 0.05, 60.0) == "lap"
    assert drive(timer, -0.05, 0.05, 125.0) == "lap"
    assert timer.lap_times == pytest.approx([60.0, 65.0])
    assert timer.laps_done == 2


def test_backward_and_jitter_crossings_do_not_count():
    sign = crossing_direction((-0.05, -1.2), (0.05, -1.2), *LINE)
    timer = LapTimer(*LINE, forward_sign=sign, min_lap_time=5.0)
    assert drive(timer, -0.05, 0.05, 0.0) == "start"
    assert drive(timer, 0.05, -0.05, 1.0) is None
    assert drive(timer, -0.05, 0.05, 2.0) is None
    assert timer.laps_done == 0


def test_crossing_outside_track_does_not_count():
    sign = crossing_direction((-0.05, -1.2), (0.05, -1.2), *LINE)
    timer = LapTimer(*LINE, forward_sign=sign)
    timer.update(-0.05, 1.2, 0.0)
    assert timer.update(0.05, 1.2, 0.1) is None
