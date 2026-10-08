"""Monitor: logs every event and tick, and works out the race metrics.

It writes runs/<timestamp>/events.csv, ticks.csv and summary.json.
Distance, contacts and clearance come from its own /odom and /scan
subscriptions, so they do not depend on the controller's numbers.

Contact event: the lowest valid LiDAR range drops below contact_enter
(0.15 m). It ends when the range rises above contact_exit (0.20 m).
The LiDAR cannot measure below 0.12 m, so 0.15 m means the body is
about 5 to 8 cm from the object.
"""

import csv
import json
import math
import os
import signal
import time
from datetime import datetime

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from apex_race import replan
from apex_race import state_machine as sm

TICK_FIELDS = ["t", "race_t", "state", "lap", "x", "y", "yaw", "speed", "cmd_v", "cmd_w",
               "curvature", "front", "corridor", "min_range", "distance", "replanning",
               "monitor_min_range", "monitor_distance", "in_contact"]
EVENT_FIELDS = ["t", "race_t", "kind", "state", "lap", "event", "old", "new", "text"]


class Monitor(Node):
    def __init__(self):
        super().__init__("monitor_node")
        p = self.declare_parameters("", [
            ("runs_dir", ""), ("car", "auto"), ("contact_enter", 0.15),
            ("contact_exit", 0.20), ("tick_rate", 5.0),
        ])
        self.cfg = {x.name: x.value for x in p}
        runs = self.cfg["runs_dir"] or os.path.join(os.getcwd(), "runs")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(runs, stamp)
        os.makedirs(self.run_dir, exist_ok=True)

        self.events_f = open(os.path.join(self.run_dir, "events.csv"), "w", newline="")
        self.events = csv.DictWriter(self.events_f, fieldnames=EVENT_FIELDS, extrasaction="ignore")
        self.events.writeheader()
        self.ticks_f = open(os.path.join(self.run_dir, "ticks.csv"), "w", newline="")
        self.ticks = csv.DictWriter(self.ticks_f, fieldnames=TICK_FIELDS, extrasaction="ignore")
        self.ticks.writeheader()

        ns = "/" + self.cfg["car"]
        self.create_subscription(String, "/apex/events", self.on_event, 50)
        self.create_subscription(String, "/apex/telemetry", self.on_telem, 20)
        self.create_subscription(Odometry, ns + "/odom", self.on_odom, 20)
        self.create_subscription(LaserScan, ns + "/scan", self.on_scan, qos_profile_sensor_data)
        self.stop_pubs = [self.create_publisher(Twist, f"/{c}/cmd_vel", 10)
                          for c in ("auto", "player")]

        self.contacts = replan.ContactCounter(self.cfg["contact_enter"], self.cfg["contact_exit"])
        self.state = sm.IDLE
        self.telem = None
        self.racing = False
        self.lowest = float("inf")
        self.scan_min = float("inf")
        self.distance = 0.0
        self.last_xy = None
        self.lap_times = []
        self.counts = {s: 0 for s in sm.STATES}
        self.transitions = 0
        self.total_time = None
        self.final_state = None
        self.cone_drop = None
        self.started_wall = time.time()
        self.summary_written = False

        self.create_timer(1.0 / self.cfg["tick_rate"], self.write_tick)
        self.get_logger().info(f"Monitor writing to {self.run_dir}")

    def on_event(self, msg):
        try:
            e = json.loads(msg.data)
        except ValueError:
            return
        self.events.writerow(e)
        self.events_f.flush()
        kind = e.get("kind")
        if kind == "transition":
            self.transitions += 1
            new = e.get("new")
            self.state = new
            self.counts[new] = self.counts.get(new, 0) + 1
            if e.get("old") == sm.COUNTDOWN and new == sm.RACING:
                self.racing = True
            if new in (sm.FINISHED, sm.ABORTED):
                self.racing = False
                self.final_state = new
                self.total_time = e.get("race_t")
                self.write_summary()
            if new == sm.IDLE:
                self.reset_metrics()
        elif kind == "lap" and e.get("lap_event") == "lap":
            self.lap_times.append(e.get("lap_time"))
        elif kind == "obstacle":
            self.cone_drop = e
        self.get_logger().info(f"[{e.get('race_t', 0):7.1f} s] {e.get('text')}")

    def reset_metrics(self):
        self.lowest = float("inf")
        self.distance = 0.0
        self.lap_times = []
        self.counts = {s: 0 for s in sm.STATES}
        self.contacts = replan.ContactCounter(self.cfg["contact_enter"], self.cfg["contact_exit"])
        self.final_state = None
        self.total_time = None
        self.summary_written = False
        self.racing = False
        self.last_xy = None

    def on_telem(self, msg):
        try:
            self.telem = json.loads(msg.data)
        except ValueError:
            pass

    def on_odom(self, msg):
        p = msg.pose.pose.position
        xy = (p.x, p.y)
        if self.racing and self.last_xy is not None and self.state in sm.MOVING:
            self.distance += math.dist(xy, self.last_xy)
        self.last_xy = xy

    def on_scan(self, msg):
        r = replan.min_range(list(msg.ranges), msg.range_min, msg.range_max)
        self.scan_min = r
        if self.racing and self.state in sm.MOVING:
            self.lowest = min(self.lowest, r)
            if self.contacts.update(r):
                self.get_logger().warn(f"Contact event {self.contacts.count}: "
                                       f"lowest range {r:.3f} m.")
                self.on_event(String(data=json.dumps({
                    "t": self.telem["t"] if self.telem else None,
                    "race_t": self.telem["race_t"] if self.telem else None,
                    "kind": "contact", "state": self.state,
                    "lap": self.telem["lap"] if self.telem else None,
                    "text": f"Contact event {self.contacts.count}. Lowest range {r:.3f} m."})))

    def write_tick(self):
        if self.telem is None:
            return
        row = dict(self.telem)
        row["monitor_min_range"] = round(self.scan_min, 3) if math.isfinite(self.scan_min) else None
        row["monitor_distance"] = round(self.distance, 3)
        row["in_contact"] = self.contacts.in_contact
        self.ticks.writerow(row)
        self.ticks_f.flush()

    def summary(self):
        return {
            "final_state": self.final_state or self.state,
            "laps_completed": len(self.lap_times),
            "lap_times_s": [round(t, 2) for t in self.lap_times],
            "best_lap_s": round(min(self.lap_times), 2) if self.lap_times else None,
            "total_race_time_s": round(self.total_time, 2) if self.total_time is not None else None,
            "distance_m": round(self.distance, 2),
            "contact_events": self.contacts.count,
            "lowest_clearance_m": round(self.lowest, 3) if math.isfinite(self.lowest) else None,
            "avoid_count": self.counts.get(sm.AVOID, 0),
            "replan_count": self.counts.get(sm.REPLAN, 0),
            "pause_count": self.counts.get(sm.PAUSED, 0),
            "state_transitions": self.transitions,
            "contact_definition": (f"lowest valid LiDAR range below {self.cfg['contact_enter']} m, "
                                   f"ends above {self.cfg['contact_exit']} m"),
            "run_dir": self.run_dir,
            "wall_clock_s": round(time.time() - self.started_wall, 1),
        }

    def write_summary(self):
        s = self.summary()
        with open(os.path.join(self.run_dir, "summary.json"), "w") as f:
            json.dump(s, f, indent=2)
        self.summary_written = True
        lines = [
            "",
            "========== APEX RACE SUMMARY ==========",
            f"Result:            {s['final_state']}",
            f"Laps:              {s['laps_completed']}",
            f"Lap times:         {', '.join(f'{t:.1f} s' for t in s['lap_times_s']) or 'none'}",
            f"Total race time:   {s['total_race_time_s']} s",
            f"Distance driven:   {s['distance_m']} m",
            f"Contact events:    {s['contact_events']}",
            f"Lowest clearance:  {s['lowest_clearance_m']} m",
            f"AVOID count:       {s['avoid_count']}",
            f"REPLAN count:      {s['replan_count']}",
            f"Pauses:            {s['pause_count']}",
            f"Logs:              {self.run_dir}",
            "=======================================",
        ]
        for line in lines:
            self.get_logger().info(line)

    def close(self):
        for pub in self.stop_pubs:
            pub.publish(Twist())
        if not self.summary_written:
            self.write_summary()
        self.events_f.close()
        self.ticks_f.close()


def raise_interrupt(*_):
    raise KeyboardInterrupt


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, raise_interrupt)
    node = Monitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.get_logger().info("Monitor shutting down. Sent zero velocity as a safety stop.")
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
