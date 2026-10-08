#!/usr/bin/env python3
"""Draw the 2D LiDAR map from one Apex run and check it against the real walls.

Usage: python3 scripts/plot_map.py RUN_DIR [--out DIR]

Reads RUN_DIR/map.yaml and map.pgm (saved by map_saver_cli after a run with
slam:=true) and RUN_DIR/ticks.csv for the racer's path. Writes two PNGs:

  map.png            the saved map as it is, with the racer's path on top
  map_vs_walls.png   the occupied cells against the wall faces from
                     circuit.yaml, and how far each occupied cell is from
                     the nearest wall face
  slam_error.png     slam_toolbox's pose error over the race, if the run has
                     slam_offset.csv (written by scripts/slam_offset.py)

It also prints the numbers and writes them to map_check.json in RUN_DIR.
The map frame starts on the odom frame, and /odom here is Gazebo's world
frame, so map and circuit coordinates can be compared directly.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "apex_race"
sys.path.insert(0, str(PKG))

from apex_race import track  # noqa: E402

OCCUPIED, FREE, UNKNOWN = 0, 1, 2


def read_pgm(path):
    """Read a binary (P5) PGM. Returns (width, height, rows), top row first."""
    data = path.read_bytes()
    fields = []
    i = 0
    while len(fields) < 4:
        while data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b"#":
            while data[i:i + 1] not in (b"\n", b""):
                i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        fields.append(data[i:j])
        i = j
    if fields[0] != b"P5":
        raise ValueError(f"{path} is not a binary PGM")
    w, h, maxval = int(fields[1]), int(fields[2]), int(fields[3])
    if maxval > 255:
        raise ValueError("16 bit PGM is not supported")
    pix = data[i + 1:i + 1 + w * h]
    return w, h, [list(pix[r * w:(r + 1) * w]) for r in range(h)]


def load_map(run):
    meta = yaml.safe_load((run / "map.yaml").read_text())
    w, h, rows = read_pgm(run / meta["image"])
    occ_t, free_t = meta["occupied_thresh"], meta["free_thresh"]
    negate = meta.get("negate", 0)
    if meta.get("mode") == "trinary" and not negate:
        # map_saver_cli writes 0 for occupied, 254 for free and 205 for unknown.
        # 205 would read as free with its own free_thresh of 0.25, so use the codes.
        codes = {0: OCCUPIED, 254: FREE, 205: UNKNOWN}
        return meta, w, h, [[codes[v] for v in row] for row in rows]
    grid = []
    for row in rows:
        out = []
        for v in row:
            p = v / 255.0 if negate else (255 - v) / 255.0
            out.append(OCCUPIED if p > occ_t else FREE if p < free_t else UNKNOWN)
        grid.append(out)
    return meta, w, h, grid


def cell_centre(meta, h, r, c):
    """World (x, y) of the cell in image row r, column c (row 0 is the top)."""
    res = meta["resolution"]
    ox, oy = meta["origin"][0], meta["origin"][1]
    return ox + (c + 0.5) * res, oy + (h - 1 - r + 0.5) * res


def stadium_distance(x, y, half):
    """Distance from (x, y) to the stadium's centre segment from (-half, 0) to (half, 0)."""
    return math.hypot(x - max(-half, min(half, x)), y)


def wall_faces(circuit):
    """Radii (from the centre segment) of the two wall faces that face the track."""
    t = circuit["track"]
    return t["turn_radius"] - t["width"] / 2, t["turn_radius"] + t["width"] / 2


def clusters(cells):
    """Group (row, col) cells that touch, including diagonally."""
    left = set(cells)
    groups = []
    while left:
        stack = [left.pop()]
        group = []
        while stack:
            r, c = stack.pop()
            group.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    n = (r + dr, c + dc)
                    if n in left:
                        left.remove(n)
                        stack.append(n)
        groups.append(group)
    return sorted(groups, key=len, reverse=True)


def racer_path(run):
    with open(run / "ticks.csv") as f:
        rows = [r for r in csv.DictReader(f) if r["state"] != "IDLE"]
    return [float(r["x"]) for r in rows], [float(r["y"]) for r in rows]


def race_start(run):
    """Sim time of the first tick after IDLE, so times match analyze_run.py."""
    with open(run / "ticks.csv") as f:
        for r in csv.DictReader(f):
            if r["state"] != "IDLE":
                return float(r["t"])
    return 0.0


def lap_starts(run, t0):
    """Times (since the start key) at which laps 2, 3, ... began."""
    with open(run / "ticks.csv") as f:
        rows = list(csv.DictReader(f))
    out = []
    for a, b in zip(rows, rows[1:]):
        if b["lap"] != a["lap"] and int(b["lap"]) > 1:
            out.append((int(b["lap"]), float(b["t"]) - t0))
    return out


def slam_error(run, out):
    """Plot slam_offset.csv. Returns the summary numbers, or None without the file."""
    path = run / "slam_offset.csv"
    if not path.exists():
        return None
    with open(path) as f:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    if not rows:
        return None
    t0 = race_start(run)
    t = [r["t"] - t0 for r in rows]
    pos = [math.hypot(r["x"], r["y"]) * 100 for r in rows]
    yaw = [math.degrees(r["yaw"]) for r in rows]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 4.6), sharex=True)
    a1.step(t, pos, where="post", color="#6a1b9a", lw=1.2)
    a1.set_ylabel("position error (cm)")
    a2.step(t, yaw, where="post", color="#00695c", lw=1.2)
    a2.axhline(0, color="k", lw=0.5)
    a2.set_ylabel("heading error (deg)")
    a2.set_xlabel("time since start key (s)")
    for ax in (a1, a2):
        for lap, tl in lap_starts(run, t0):
            ax.axvline(tl, color="#9e9e9e", ls=":", lw=1)
            if ax is a1:
                ax.text(tl + 1, max(pos) * 0.92 if max(pos) > 0 else 0.5, f"lap {lap}", fontsize=8)
        ax.grid(alpha=0.3)
    a1.set_title("slam_toolbox pose error (map to odom offset; /odom here is the true pose)")
    fig.tight_layout()
    fig.savefig(out / "slam_error.png", dpi=150)
    plt.close(fig)
    racing = [(ti, pi, yi) for ti, pi, yi in zip(t, pos, yaw) if ti >= 0]
    return {
        "max_position_error_m": round(max(p for _, p, _ in racing) / 100, 3) if racing else None,
        "final_position_error_m": round(pos[-1] / 100, 3),
        "max_abs_heading_error_deg": round(max(abs(y) for _, _, y in racing), 2) if racing else None,
        "final_heading_error_deg": round(yaw[-1], 2),
    }


def draw_faces(ax, circuit, label):
    half = circuit["track"]["straight_length"] / 2
    for i, radius in enumerate(wall_faces(circuit)):
        pts = track.centre_line(2 * half, radius, 0.02)
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        ax.plot(xs, ys, color="#d32f2f", lw=0.8, ls="--", label=label if i == 0 else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--circuit", default=str(PKG / "config" / "circuit.yaml"))
    ap.add_argument("--near", type=float, default=0.05,
                    help="an occupied cell this close to a wall face counts as on the wall (m)")
    ap.add_argument("--far", type=float, default=0.15,
                    help="occupied cells farther than this from both faces are listed as other objects (m)")
    args = ap.parse_args()
    out = args.out or args.run / "figures"
    out.mkdir(parents=True, exist_ok=True)

    meta, w, h, grid = load_map(args.run)
    res = meta["resolution"]
    circuit = track.load_circuit(args.circuit)
    half = circuit["track"]["straight_length"] / 2
    inner, outer = wall_faces(circuit)

    occ = [(r, c) for r in range(h) for c in range(w) if grid[r][c] == OCCUPIED]
    n_free = sum(row.count(FREE) for row in grid)
    errors = []
    far_cells = []
    for r, c in occ:
        x, y = cell_centre(meta, h, r, c)
        d = stadium_distance(x, y, half)
        e = min(abs(d - inner), abs(d - outer))
        errors.append(e)
        if e > args.far:
            far_cells.append((r, c))
    errors_sorted = sorted(errors)
    median = errors_sorted[len(errors_sorted) // 2] if errors_sorted else float("nan")
    p95 = errors_sorted[int(0.95 * (len(errors_sorted) - 1))] if errors_sorted else float("nan")
    on_wall = sum(1 for e in errors if e <= args.near)
    others = []
    for g in clusters(far_cells):
        xs, ys = zip(*(cell_centre(meta, h, r, c) for r, c in g))
        others.append({"cells": len(g), "x": round(sum(xs) / len(xs), 2),
                       "y": round(sum(ys) / len(ys), 2)})

    check = {
        "map_size_m": [round(w * res, 2), round(h * res, 2)],
        "resolution_m": res,
        "free_area_m2": round(n_free * res * res, 2),
        "occupied_cells": len(occ),
        "occupied_within_near_of_a_wall_face": on_wall,
        "near_m": args.near,
        "share_on_wall": round(on_wall / len(occ), 3) if occ else None,
        "median_distance_to_wall_face_m": round(median, 3),
        "p95_distance_to_wall_face_m": round(p95, 3),
        "max_distance_to_wall_face_m": round(errors_sorted[-1], 3) if errors_sorted else None,
        "far_m": args.far,
        "objects_off_the_walls": others,
    }
    err = slam_error(args.run, out)
    if err is not None:
        check["slam_pose_error"] = err
    (args.run / "map_check.json").write_text(json.dumps(check, indent=2) + "\n")
    print(json.dumps(check, indent=2))

    extent = (meta["origin"][0], meta["origin"][0] + w * res,
              meta["origin"][1], meta["origin"][1] + h * res)
    cmap = ListedColormap(["#000000", "#ffffff", "#b0b0b0"])
    px, py = racer_path(args.run)

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=2, extent=extent, interpolation="nearest")
    ax.plot(px, py, color="#e65100", lw=0.8, alpha=0.8, label="racer path (odometry)")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"2D LiDAR map from slam_toolbox ({res * 100:.1f} cm cells)\n"
                 "black: occupied, white: free, grey: not seen")
    ax.legend(loc="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "map.png", dpi=150)
    plt.close(fig)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.4),
                                 gridspec_kw={"width_ratios": [1.8, 1]})
    ox = [cell_centre(meta, h, r, c) for r, c in occ]
    a1.plot([p[0] for p in ox], [p[1] for p in ox], ",", color="k")
    a1.plot([], [], "s", color="k", ms=3, label="occupied map cell")
    draw_faces(a1, circuit, "wall face from circuit.yaml")
    for o in (o for o in others if o["cells"] >= 5):
        a1.annotate(f"{o['cells']} cells\n({o['x']}, {o['y']})", (o["x"], o["y"]),
                    xytext=(o["x"] + 0.25, o["y"] + 0.3), fontsize=7,
                    arrowprops={"arrowstyle": "->", "lw": 0.6})
    a1.set_aspect("equal")
    a1.set_xlabel("x (m)")
    a1.set_ylabel("y (m)")
    a1.set_title(f"Occupied cells against the real wall faces\n"
                 f"(labels: groups of 5 or more cells over {args.far * 100:.0f} cm from a wall)")
    a1.legend(loc="center", fontsize=8)
    cm = [e * 100 for e in errors]
    a2.hist(cm, bins=[i * 0.5 for i in range(int(max(cm) / 0.5) + 2)] if cm else 10,
            color="#455a64")
    a2.axvline(median * 100, color="#d32f2f", lw=1, ls="--",
               label=f"median {median * 100:.1f} cm")
    a2.set_xlabel("distance from occupied cell to nearest wall face (cm)")
    a2.set_ylabel("cells")
    a2.set_title(f"{on_wall} of {len(occ)} occupied cells within {args.near * 100:.0f} cm of a wall")
    a2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "map_vs_walls.png", dpi=150)
    plt.close(fig)
    extra = " and slam_error.png" if err is not None else ""
    print(f"Wrote map.png, map_vs_walls.png{extra} to {out}")


if __name__ == "__main__":
    main()
