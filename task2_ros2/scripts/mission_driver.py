#!/usr/bin/env python3
"""Press the race keys for a headless test run, the same way a person would.

It sends g once the controller is up, p (pause) when the racer reaches
x > pause_x on the front straight of lap 3, and p (resume) pause_s seconds
later. It exits when the race finishes or aborts.

With --park X Y it also stands in for the person on the player car: it
drives the player car to (X, Y) and parks it there, using /player/odom,
and only then presses g.

Run inside the container:  python3 scripts/mission_driver.py
For the recorded run, press the keys yourself with keyboard_node instead.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

PKG = Path(__file__).resolve().parent.parent / "apex_race"
sys.path.insert(0, str(PKG))

from apex_race import pursuit, track  # noqa: E402


class Driver(Node):
    def __init__(self, args):
        super().__init__("mission_driver")
        self.args = args
        self.pub = self.create_publisher(String, "/apex/command", 10)
        self.create_subscription(String, "/apex/telemetry", self.on_telem, 10)
        self.started = False
        self.paused_at = None
        self.resumed = False
        self.done = False
        self.park = args.park
        self.player_offset = None
        self.parked = False
        if self.park:
            g = track.load_circuit(PKG / "config" / "circuit.yaml")["grid"]["player"]
            self.player_grid = (g["x"], g["y"], g["yaw"])
            self.player_pub = self.create_publisher(Twist, "/player/cmd_vel", 10)
            self.create_subscription(Odometry, "/player/odom", self.on_player_odom, 10)

    def on_player_odom(self, msg):
        p = msg.pose.pose
        q = p.orientation
        raw = (p.position.x, p.position.y,
               math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
        if self.player_offset is None:
            self.player_offset = pursuit.compose(self.player_grid, pursuit.inverse(raw))
        x, y, yaw = pursuit.compose(self.player_offset, raw)
        cmd = Twist()
        if not self.parked:
            fwd, left = pursuit.to_robot_frame(self.park[0], self.park[1], x, y, yaw)
            dist = math.hypot(fwd, left)
            if dist < 0.04:
                self.parked = True
                self.get_logger().info(f"Player car parked at ({x:.2f}, {y:.2f}).")
            else:
                heading = math.atan2(left, fwd)
                cmd.angular.z = max(-1.0, min(1.0, 2.0 * heading))
                cmd.linear.x = min(0.15, 0.5 * dist) if abs(heading) < 0.5 else 0.0
        self.player_pub.publish(cmd)

    def key(self, k):
        self.pub.publish(String(data=k))
        self.get_logger().info(f"Pressed {k}.")

    def on_telem(self, msg):
        t = json.loads(msg.data)
        st = t["state"]
        if not self.started and st == "IDLE" and (not self.park or self.parked):
            self.started = True
            self.key("g")
        elif (self.paused_at is None and t["lap"] == self.args.pause_lap and
              t["x"] > self.args.pause_x and t["y"] < 0 and st == "RACING"):
            self.paused_at = time.monotonic()
            self.key("p")
        elif (self.paused_at is not None and not self.resumed and st == "PAUSED" and
              time.monotonic() - self.paused_at >= self.args.pause_s):
            self.resumed = True
            self.key("p")
        elif st in ("FINISHED", "ABORTED"):
            self.done = True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pause-lap", type=int, default=3)
    ap.add_argument("--pause-x", type=float, default=0.5)
    ap.add_argument("--pause-s", type=float, default=5.0)
    ap.add_argument("--park", type=float, nargs=2, metavar=("X", "Y"),
                    help="drive the player car here and park it")
    args = ap.parse_args()
    rclpy.init()
    node = Driver(args)
    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)
    if node.park:
        node.player_pub.publish(Twist())
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
