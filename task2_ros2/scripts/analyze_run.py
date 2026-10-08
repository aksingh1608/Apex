#!/usr/bin/env python3
"""Make figures from one Apex run.

Usage: python3 scripts/analyze_run.py RUN_DIR [--out DIR]

Reads RUN_DIR/ticks.csv, events.csv and summary.json. Writes five PNGs:
path_by_state, state_timeline, speed, front_range, lap_times.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "apex_race"
sys.path.insert(0, str(PKG))

from apex_race import track  # noqa: E402
from apex_race import state_machine as sm  # noqa: E402

COLOURS = {
    sm.IDLE: "#9e9e9e", sm.COUNTDOWN: "#795548", sm.RACING: "#2e7d32",
    sm.AVOID: "#e65100", sm.REPLAN: "#6a1b9a", sm.PAUSED: "#1565c0",
    sm.FINISHED: "#000000", sm.ABORTED: "#c62828",
}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def load(run):
    with open(run / "ticks.csv") as f:
        ticks = list(csv.DictReader(f))
    with open(run / "events.csv") as f:
        events = list(csv.DictReader(f))
    summary = json.loads((run / "summary.json").read_text())
    return ticks, events, summary


def race_ticks(ticks):
    """Ticks from the start of COUNTDOWN onward, with time from that moment."""
    start = next((i for i, r in enumerate(ticks) if r["state"] != sm.IDLE), 0)
    rows = ticks[start:]
    t0 = num(rows[0]["t"]) if rows else 0.0
    for r in rows:
        r["time"] = num(r["t"]) - t0
    return rows


def draw_track(ax, circuit):
    t = circuit["track"]
    s, r, w = t["straight_length"], t["turn_radius"], t["width"]
    for radius, style in ((r - w / 2, "-"), (r + w / 2, "-"), (r, ":")):
        pts = track.centre_line(s, radius, 0.05)
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        ax.plot(xs, ys, style, color="#757575", lw=1.0 if style == "-" else 0.7)
    a, b = track.finish_line(circuit)
    ax.plot([a[0], b[0]], [a[1], b[1]], color="k", lw=2.5)
    ax.text(a[0] + 0.05, a[1] - 0.15, "finish line", fontsize=8)


def segments_by_state(rows):
    seg = []
    for r in rows:
        if seg and seg[-1][0] == r["state"]:
            seg[-1][1].append(r)
        else:
            seg.append((r["state"], [r]))
    return seg


def fig_path(rows, events, circuit, out):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    draw_track(ax, circuit)
    seg = segments_by_state(rows)
    seen = set()
    prev = None
    for state, rs in seg:
        xs = [num(r["x"]) for r in rs]
        ys = [num(r["y"]) for r in rs]
        if prev is not None:
            xs.insert(0, num(prev["x"]))
            ys.insert(0, num(prev["y"]))
        label = state if state not in seen else None
        seen.add(state)
        ax.plot(xs, ys, color=COLOURS.get(state, "k"), lw=2.2 if state != sm.RACING else 1.2,
                label=label)
        prev = rs[-1]
    cone = next((e for e in events if e["kind"] == "obstacle"), None)
    if cone is not None:
        cfg_x, cfg_y = cone_xy(cone["text"])
        if cfg_x is not None:
            ax.plot(cfg_x, cfg_y, marker="^", ms=12, color="#ff6f00", mec="k", ls="none",
                    label="dropped cone")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Racer path, coloured by state")
    ax.legend(loc="center", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "path_by_state.png", dpi=150)
    plt.close(fig)


def cone_xy(text):
    try:
        inside = text.split("(")[1].split(")")[0]
        x, y = (float(v) for v in inside.split(","))
        return x, y
    except (IndexError, ValueError):
        return None, None


def fig_timeline(rows, out):
    fig, ax = plt.subplots(figsize=(10, 2.8))
    order = [s for s in sm.STATES]
    for state, rs in segments_by_state(rows):
        t0 = rs[0]["time"]
        t1 = rs[-1]["time"] + 0.2
        ax.barh(order.index(state), t1 - t0, left=t0, color=COLOURS[state], height=0.6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("time since start key (s)")
    ax.set_title("State timeline")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "state_timeline.png", dpi=150)
    plt.close(fig)


def shade_states(ax, rows):
    for state, rs in segments_by_state(rows):
        if state in (sm.AVOID, sm.REPLAN, sm.PAUSED):
            ax.axvspan(rs[0]["time"], rs[-1]["time"] + 0.2, color=COLOURS[state], alpha=0.18,
                       lw=0)


def legend_patches(ax):
    from matplotlib.patches import Patch
    return [Patch(color=COLOURS[s], alpha=0.3, label=s) for s in (sm.AVOID, sm.REPLAN, sm.PAUSED)]


def fig_speed(rows, out):
    fig, ax = plt.subplots(figsize=(10, 3.2))
    t = [r["time"] for r in rows]
    ax.plot(t, [num(r["speed"]) for r in rows], lw=1.2, label="odometry speed")
    ax.plot(t, [num(r["cmd_v"]) for r in rows], lw=0.8, ls="--", label="commanded speed")
    shade_states(ax, rows)
    ax.set_xlabel("time since start key (s)")
    ax.set_ylabel("m/s")
    ax.set_title("Speed over time (shaded: AVOID, REPLAN, PAUSED)")
    h, _ = ax.get_legend_handles_labels()
    ax.legend(handles=h + legend_patches(ax), fontsize=8, loc="lower right", ncol=5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "speed.png", dpi=150)
    plt.close(fig)


def fig_front(rows, out, avoid_distance):
    fig, ax = plt.subplots(figsize=(10, 3.2))
    t = [r["time"] for r in rows]
    ax.plot(t, [num(r["front"]) for r in rows], lw=1.0, label="front range (+-20 deg)")
    ax.plot(t, [num(r["corridor"]) for r in rows], lw=1.0, label="corridor distance")
    ax.axhline(avoid_distance, color="#e65100", ls="--", lw=1,
               label=f"avoid distance {avoid_distance} m")
    shade_states(ax, rows)
    ax.set_ylim(0, 3.6)
    ax.set_xlabel("time since start key (s)")
    ax.set_ylabel("m")
    ax.set_title("LiDAR range ahead over time")
    h, _ = ax.get_legend_handles_labels()
    ax.legend(handles=h + legend_patches(ax), fontsize=8, loc="upper right", ncol=3)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "front_range.png", dpi=150)
    plt.close(fig)


def fig_laps(summary, events, out):
    laps = summary["lap_times_s"]
    notes = {}
    for e in events:
        lap = int(num(e["lap"])) if e["lap"] not in ("", None) else 0
        if e["kind"] == "transition" and e["new"] in (sm.AVOID, sm.REPLAN, sm.PAUSED):
            notes.setdefault(lap, set()).add(e["new"])
        if e["kind"] == "obstacle":
            notes.setdefault(lap, set()).add("cone")
    fig, ax = plt.subplots(figsize=(6, 3.6))
    xs = list(range(1, len(laps) + 1))
    bars = ax.bar(xs, laps, color="#455a64")
    for x, b in zip(xs, bars):
        label = f"{b.get_height():.1f} s"
        extra = notes.get(x)
        if extra:
            label += "\n" + ", ".join(sorted(extra))
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, label, ha="center",
                fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"Lap {x}" for x in xs])
    ax.set_ylabel("lap time (s)")
    ax.set_ylim(0, max(laps) * 1.3 if laps else 1)
    ax.set_title("Lap times (paused time not counted)")
    fig.tight_layout()
    fig.savefig(out / "lap_times.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--circuit", default=str(PKG / "config" / "circuit.yaml"))
    ap.add_argument("--params", default=str(PKG / "config" / "params.yaml"))
    args = ap.parse_args()
    with open(args.params) as f:
        avoid = yaml.safe_load(f)["race_controller_node"]["ros__parameters"]["avoid_distance"]
    out = args.out or args.run / "figures"
    out.mkdir(parents=True, exist_ok=True)
    ticks, events, summary = load(args.run)
    rows = race_ticks(ticks)
    circuit = track.load_circuit(args.circuit)
    fig_path(rows, events, circuit, out)
    fig_timeline(rows, out)
    fig_speed(rows, out)
    fig_front(rows, out, avoid)
    fig_laps(summary, events, out)
    print(f"Wrote 5 figures to {out}")


if __name__ == "__main__":
    main()
