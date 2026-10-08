#!/usr/bin/env python3
"""Build worlds/apex_circuit.world from config/circuit.yaml.

Usage: python3 world_gen/generate_world.py [--circuit FILE] [--out FILE]

Everything is made from boxes, cylinders and spheres. No meshes.
"""

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "apex_race"
sys.path.insert(0, str(PKG))

from apex_race import props, track  # noqa: E402
from apex_race.props import BLACK, WHITE, part, static_model  # noqa: E402

ASPHALT = (0.22, 0.22, 0.24)
GRASS = (0.25, 0.5, 0.22)
KERB_RED = (0.85, 0.1, 0.1)
GREY = (0.55, 0.55, 0.58)
SEAT = (0.35, 0.37, 0.42)
CROWD = [(0.85, 0.15, 0.15), (0.15, 0.35, 0.85), (0.95, 0.8, 0.1),
         (0.15, 0.65, 0.3), (0.6, 0.2, 0.7), (0.95, 0.5, 0.1)]


def surface_model(c):
    """Flat track and infield. Visual only, so the wheels touch the ground plane."""
    t = c["track"]
    s, r, w = t["straight_length"], t["turn_radius"], t["width"]
    outer, inner = r + w / 2, r - w / 2
    half = s / 2
    parts = [
        part("asphalt_mid", "box", (s, 2 * outer, 0.002), (0, 0, 0.001, 0), ASPHALT, collide=False),
        part("asphalt_e", "cylinder", (outer, 0.002), (half, 0, 0.001, 0), ASPHALT, collide=False),
        part("asphalt_w", "cylinder", (outer, 0.002), (-half, 0, 0.001, 0), ASPHALT, collide=False),
        part("infield_mid", "box", (s, 2 * inner, 0.002), (0, 0, 0.003, 0), GRASS, collide=False),
        part("infield_e", "cylinder", (inner, 0.002), (half, 0, 0.003, 0), GRASS, collide=False),
        part("infield_w", "cylinder", (inner, 0.002), (-half, 0, 0.003, 0), GRASS, collide=False),
    ]
    # Chequered finish line across the front straight.
    x = c["finish_line_x"]
    n = 12
    sq = w / n
    for i in range(n):
        for j in range(2):
            rgb = WHITE if (i + j) % 2 == 0 else BLACK
            parts.append(part(f"line_{i}_{j}", "box", (sq, sq, 0.002),
                              (x - sq / 2 + j * sq, -outer + sq * (i + 0.5), 0.004, 0),
                              rgb, collide=False))
    # Grid boxes: a white U shape behind each start position.
    for name, g in c["grid"].items():
        gx, gy = g["x"], g["y"]
        parts.append(part(f"grid_{name}_back", "box", (0.02, 0.3, 0.002),
                          (gx - 0.15, gy, 0.004, 0), WHITE, collide=False))
        for side in (-1, 1):
            parts.append(part(f"grid_{name}_{side}", "box", (0.3, 0.02, 0.002),
                              (gx, gy + side * 0.15, 0.004, 0), WHITE, collide=False))
    return static_model("track_surface", parts)


def walls_model(c):
    t, wl = c["track"], c["walls"]
    s, r, w = t["straight_length"], t["turn_radius"], t["width"]
    th, h = wl["thickness"], wl["height"]
    outer = props.stadium_outline(s, r + w / 2 + th / 2, wl["arc_step_deg"], 0.5)
    inner = props.stadium_outline(s, r - w / 2 - th / 2, wl["arc_step_deg"], 0.5)
    parts = props.wall_ring("outer", outer, 0.5, th, h, [KERB_RED, WHITE])
    parts += props.wall_ring("inner", inner, 0.5, th, h, [WHITE, KERB_RED])
    return static_model("barrier_walls", parts)


def gantry_model(c):
    t, g = c["track"], c["gantry"]
    r, w = t["turn_radius"], t["width"]
    x = c["finish_line_x"]
    th = c["walls"]["thickness"]
    y_out = -(r + w / 2 + th + 0.08)
    y_in = -(r - w / 2 - th - 0.08)
    span = y_in - y_out
    mid = (y_in + y_out) / 2
    h = g["height"]
    col = tuple(g["colour"])
    parts = [
        part("post_out", "box", (0.08, 0.08, h), (x, y_out, h / 2, 0), col),
        part("post_in", "box", (0.08, 0.08, h), (x, y_in, h / 2, 0), col),
        part("beam", "box", (0.1, span + 0.08, 0.12), (x, mid, h + 0.06, 0), col),
    ]
    # Five start lights on the beam, lit green.
    for i in range(5):
        parts.append(part(f"light_{i}", "sphere", (0.03,),
                          (x - 0.06, mid - 0.3 + 0.15 * i, h + 0.06, 0),
                          (0.1, 0.9, 0.2), collide=False, emissive=(0.1, 0.8, 0.2)))
    return static_model("start_finish_gantry", parts)


def pit_model(c):
    t, p = c["track"], c["pit_lane"]
    s, r, w = t["straight_length"], t["turn_radius"], t["width"]
    edge = -(r + w / 2 + c["walls"]["thickness"] + p["offset"])
    y_lane = edge - p["width"] / 2
    parts = [
        part("pit_lane", "box", (p["length"], p["width"], 0.002), (0, y_lane, 0.002, 0),
             GREY, collide=False),
        part("pit_line", "box", (p["length"], 0.02, 0.002), (0, edge, 0.004, 0),
             WHITE, collide=False),
    ]
    n = p["boxes"]
    box_w = p["length"] / n
    y_box = edge - p["width"] - 0.25
    for i in range(n):
        x = -p["length"] / 2 + box_w * (i + 0.5)
        parts.append(part(f"garage_{i}_roof", "box", (box_w - 0.05, 0.5, 0.04),
                          (x, y_box, 0.42, 0), (0.9, 0.9, 0.92)))
        parts.append(part(f"garage_{i}_back", "box", (box_w - 0.05, 0.04, 0.4),
                          (x, y_box - 0.23, 0.2, 0), GREY))
        parts.append(part(f"garage_{i}_side", "box", (0.04, 0.5, 0.4),
                          (x - box_w / 2 + 0.05, y_box, 0.2, 0), GREY))
        parts.append(part(f"garage_{i}_mark", "box", (box_w * 0.6, 0.3, 0.002),
                          (x, y_box + 0.05, 0.004, 0), CROWD[i % len(CROWD)], collide=False))
    return static_model("pit_lane", parts)


def grandstand_model(c, idx, g):
    t = c["track"]
    r, w = t["turn_radius"], t["width"]
    y0 = r + w / 2 + c["walls"]["thickness"] + 0.35
    row_depth, row_rise = 0.3, 0.15
    seats = g["seats"]
    length = seats * 0.2 + 0.1
    parts = []
    k = 0
    for row in range(g["rows"]):
        y = y0 + row_depth * (row + 0.5)
        top = row_rise * (row + 1)
        parts.append(part(f"row_{row}", "box", (length, row_depth, top),
                          (0, y, top / 2, 0), SEAT))
        for s in range(seats):
            x = -length / 2 + 0.15 + 0.2 * s
            rgb = CROWD[(k + idx * 3) % len(CROWD)]
            parts += props.spectator_parts(f"fan_{row}_{s}", x, y, top, rgb)
            k += 1
    back_y = y0 + row_depth * g["rows"] + 0.02
    roof_h = row_rise * g["rows"] + 0.45
    parts.append(part("back", "box", (length, 0.04, roof_h), (0, back_y, roof_h / 2, 0), GREY))
    parts.append(part("roof", "box", (length, row_depth * g["rows"] + 0.1, 0.03),
                      (0, y0 + row_depth * g["rows"] / 2, roof_h, 0), (0.9, 0.9, 0.92)))
    return static_model(f"grandstand_{idx}", parts, x=g["x"])


def light_tower_model(c):
    lt = c["light_tower"]
    h = lt["height"]
    parts = [
        part("pole", "cylinder", (0.04, h), (0, 0, h / 2, 0), GREY),
        part("head", "box", (0.35, 0.1, 0.2), (0, 0, h + 0.1, 0), BLACK),
    ]
    for i in range(3):
        parts.append(part(f"lamp_{i}", "box", (0.08, 0.02, 0.12),
                          (-0.11 + 0.11 * i, -0.06, h + 0.1, 0), (1, 1, 0.85),
                          collide=False, emissive=(1, 1, 0.8)))
    yaw = math.atan2(-lt["y"], -lt["x"]) + math.pi / 2
    return static_model("light_tower", parts, x=lt["x"], y=lt["y"], yaw=yaw)


def banner_model(c, idx, b):
    t = c["track"]
    r, w = t["turn_radius"], t["width"]
    y = r + w / 2 + c["walls"]["thickness"] + 0.12
    y = -y if b["side"] == "front" else y
    col = tuple(b["colour"])
    parts = [
        part("board", "box", (0.9, 0.03, 0.25), (0, 0, 0.42, 0), col),
        part("leg_a", "box", (0.03, 0.03, 0.3), (-0.4, 0, 0.15, 0), GREY),
        part("leg_b", "box", (0.03, 0.03, 0.3), (0.4, 0, 0.15, 0), GREY),
    ]
    return static_model(f"banner_{idx}", parts, x=b["x"], y=y)


def world_sdf(c):
    models = [surface_model(c), walls_model(c), gantry_model(c), pit_model(c),
              light_tower_model(c)]
    models += [grandstand_model(c, i, g) for i, g in enumerate(c["grandstands"])]
    models += [banner_model(c, i, b) for i, b in enumerate(c["banners"])]
    models += [static_model(f"cone_{i}", props.cone_parts(f"cone{i}"), x=x, y=y)
               for i, (x, y) in enumerate(c["cones"])]
    models += [static_model(f"tyre_stack_{i}", props.tyre_stack_parts(f"ts{i}"), x=x, y=y)
               for i, (x, y) in enumerate(c["tyre_stacks"])]
    body = "\n\n".join(models)
    return f"""<?xml version="1.0"?>
<!-- Generated by world_gen/generate_world.py from config/circuit.yaml. Do not edit by hand. -->
<sdf version="1.6">
<world name="apex_circuit">
<physics type="ode">
  <real_time_update_rate>1000.0</real_time_update_rate>
  <max_step_size>0.001</max_step_size>
  <real_time_factor>1</real_time_factor>
</physics>
<scene>
  <ambient>0.55 0.55 0.55 1</ambient>
  <background>0.7 0.82 0.95 1</background>
  <shadows>false</shadows>
</scene>
<gui fullscreen="0">
  <camera name="user_camera">
    <pose>0 -6.5 5.5 0 0.72 1.5708</pose>
  </camera>
</gui>
<light name="sun" type="directional">
  <cast_shadows>false</cast_shadows>
  <pose>0 0 10 0 0 0</pose>
  <diffuse>0.85 0.85 0.85 1</diffuse>
  <specular>0.2 0.2 0.2 1</specular>
  <direction>-0.4 0.3 -0.9</direction>
</light>
<plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
  <ros><namespace>/gazebo</namespace></ros>
  <update_rate>10.0</update_rate>
</plugin>
<model name="ground_plane">
  <static>true</static>
  <link name="link">
    <collision name="collision">
      <geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
      <surface><friction><ode><mu>100</mu><mu2>50</mu2></ode></friction></surface>
    </collision>
    <visual name="visual">
      <geometry><plane><normal>0 0 1</normal><size>40 40</size></plane></geometry>
      {props.material((0.3, 0.55, 0.27))}
    </visual>
  </link>
</model>

{body}

</world>
</sdf>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuit", default=str(PKG / "config" / "circuit.yaml"))
    ap.add_argument("--out", default=str(PKG / "worlds" / "apex_circuit.world"))
    args = ap.parse_args()
    c = track.load_circuit(args.circuit)
    text = world_sdf(c)
    Path(args.out).write_text(text)
    print(f"Wrote {args.out} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
