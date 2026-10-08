import math
from pathlib import Path

import pytest

from apex_race import track

CIRCUIT = Path(__file__).resolve().parents[1] / "config" / "circuit.yaml"


def test_centre_line_length_and_spacing():
    pts = track.centre_line(3.0, 1.2, 0.1)
    expected = 2 * 3.0 + 2 * math.pi * 1.2
    assert track.path_length(pts) == pytest.approx(expected, rel=0.01)
    gaps = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    assert max(gaps) < 0.11


def test_centre_line_is_counterclockwise():
    pts = track.centre_line(3.0, 1.2, 0.1)
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2
    assert area > 0


def test_points_sit_on_centre_line():
    for x, y in track.centre_line(3.0, 1.2, 0.1):
        assert track.distance_to_centre_line(x, y, 3.0, 1.2) == pytest.approx(0.0, abs=1e-9)


def test_circuit_file_is_consistent():
    c = track.load_circuit(CIRCUIT)
    a, b = track.finish_line(c)
    assert a[0] == b[0] == c["finish_line_x"]
    half_w = c["track"]["width"] / 2
    for name, g in c["grid"].items():
        d = track.distance_to_centre_line(g["x"], g["y"], c["track"]["straight_length"],
                                          c["track"]["turn_radius"])
        assert abs(d) < half_w - 0.15, name
        assert g["x"] < c["finish_line_x"], name
