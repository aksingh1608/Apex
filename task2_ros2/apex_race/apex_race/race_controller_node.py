"""Race controller: state machine, pure pursuit over waypoints, LiDAR avoidance.

Inputs:  /<car>/odom, /<car>/scan, /apex/command (keys g p x r)
Outputs: /<car>/cmd_vel, /apex/status (1 Hz), /apex/telemetry, /apex/events
"""

import json
import math
import os
import signal

import rclpy
from ament_index_python.packages import get_package_share_directory
from gazebo_msgs.msg import EntityState
from gazebo_msgs.srv import DeleteEntity, SetEntityState
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from apex_race import laps, pursuit, replan, track
from apex_race import state_machine as sm


def yaw_from_quat(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class RaceController(Node):
    def __init__(self):
        super().__init__("race_controller_node")
        p = self.declare_parameters("", [
            ("circuit_file", ""), ("car", "auto"), ("laps", 3),
            ("control_rate", 10.0), ("status_rate", 1.0), ("countdown_s", 3.0),
            ("lookahead", 0.45), ("v_max", 0.22), ("v_min", 0.08),
            ("curvature_gain", 0.6), ("w_max", 1.5), ("search_window", 40),
            ("corridor_half_width", 0.17), ("avoid_distance", 0.45),
            ("clear_distance", 0.8), ("avoid_hold_s", 1.0),
            ("gap_ahead", 1.0), ("gap_cap", 1.0), ("replan_clearance", 0.25),
            ("replan_offset_min", 0.30), ("replan_offset_max", 0.38),
            ("replan_points", 22), ("replan_ramp", 3),
            ("replan_speed", 0.12), ("replan_stop_distance", 0.15),
            ("replan_stop_half_width", 0.1), ("min_lap_time", 20.0),
        ])
        self.cfg = {x.name: x.value for x in p}
        cfg = self.cfg

        circuit_file = cfg["circuit_file"] or os.path.join(
            get_package_share_directory("apex_race"), "config", "circuit.yaml")
        self.circuit = track.load_circuit(circuit_file)
        self.base_wps = track.circuit_waypoints(self.circuit)
        self.wps = list(self.base_wps)
        g = self.circuit["grid"][cfg["car"]]
        self.grid = (g["x"], g["y"], g["yaw"])
        line_a, line_b = track.finish_line(self.circuit)
        fwd = laps.crossing_direction((-0.05, line_a[1] + 0.3), (0.05, line_a[1] + 0.3),
                                      line_a, line_b)
        self.lap_timer = laps.LapTimer(line_a, line_b, forward_sign=fwd,
                                       min_lap_time=cfg["min_lap_time"])

        ns = "/" + cfg["car"]
        self.cmd_pub = self.create_publisher(Twist, ns + "/cmd_vel", 10)
        self.status_pub = self.create_publisher(String, "/apex/status", 10)
        self.telem_pub = self.create_publisher(String, "/apex/telemetry", 10)
        self.event_pub = self.create_publisher(String, "/apex/events", 50)
        self.create_subscription(Odometry, ns + "/odom", self.on_odom, 20)
        self.create_subscription(LaserScan, ns + "/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(String, "/apex/command", self.on_command, 10)
        self.set_state_cli = self.create_client(SetEntityState, "/gazebo/set_entity_state")
        self.delete_cli = self.create_client(DeleteEntity, "/delete_entity")

        self.state = sm.IDLE
        self.odom_offset = None
        self.pose = None
        self.speed = 0.0
        self.scan = None
        self.scan_pts = []
        self.front = float("inf")
        self.corridor = float("inf")
        self.min_r = float("inf")
        self.idx = None
        self.cmd = (0.0, 0.0)
        self.kappa = 0.0
        self.distance = 0.0
        self.last_xy = None
        self.race_time = 0.0
        self.last_tick = None
        self.state_since = 0.0
        self.countdown_said = None
        self.replan_end = None
        self.replan_side = None

        self.create_timer(1.0 / cfg["control_rate"], self.tick)
        self.create_timer(1.0 / cfg["status_rate"], self.publish_status)
        self.say("info", f"Race controller ready for car {cfg['car']}. "
                         f"{len(self.base_wps)} waypoints, {cfg['laps']} laps. Press g to start.")

    # ----- inputs -----

    def on_odom(self, msg):
        p = msg.pose.pose
        raw = (p.position.x, p.position.y, yaw_from_quat(p.orientation))
        if self.odom_offset is None:
            # The car starts on its grid slot. Map the odom frame onto the world.
            self.odom_offset = pursuit.compose(self.grid, pursuit.inverse(raw))
        self.pose = pursuit.compose(self.odom_offset, raw)
        self.speed = msg.twist.twist.linear.x
        xy = self.pose[:2]
        if self.last_xy is not None and self.state in sm.MOVING:
            self.distance += math.dist(xy, self.last_xy)
        self.last_xy = xy

    def on_scan(self, msg):
        self.scan = msg
        r = list(msg.ranges)
        self.scan_pts = replan.scan_points(r, msg.angle_min, msg.angle_increment,
                                           msg.range_min, msg.range_max)
        self.front = replan.front_range(r, msg.angle_min, msg.angle_increment,
                                        math.radians(20), msg.range_min, msg.range_max)
        self.corridor = replan.corridor_distance(self.scan_pts, self.cfg["corridor_half_width"],
                                                 msg.range_max)
        self.min_r = replan.min_range(r, msg.range_min, msg.range_max)

    def on_command(self, msg):
        key = msg.data.strip().lower()[:1]
        event = sm.key_to_event(key, self.state)
        if event is None:
            return
        if event == sm.RESET:
            if self.fire(event):
                self.reset_race()
            return
        if self.fire(event) and event == sm.RESUME:
            # Start clean after a pause. If the obstacle is still there,
            # RACING sees it on the next tick and goes back to AVOID.
            self.end_replan()

    # ----- state machine -----

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def fire(self, event, **values):
        new = sm.next_state(self.state, event)
        if new is None:
            return False
        values.setdefault("front", self.corridor)
        text = sm.sentence(self.state, new, event, **values)
        old = self.state
        self.state = new
        self.state_since = self.now()
        self.say("transition", text, old=old, new=new, event=event)
        if new in (sm.PAUSED, sm.FINISHED, sm.ABORTED, sm.IDLE, sm.AVOID):
            self.send(0.0, 0.0)
        if new == sm.FINISHED:
            self.say_summary()
        return True

    def say(self, kind, text, **extra):
        msg = {"t": round(self.now(), 3), "race_t": round(self.race_time, 3),
               "kind": kind, "state": self.state, "lap": self.current_lap(), "text": text}
        msg.update(extra)
        self.event_pub.publish(String(data=json.dumps(msg)))
        self.get_logger().info(text)

    def say_summary(self):
        lt = self.lap_timer.lap_times
        laps_txt = ", ".join(f"{t:.1f} s" for t in lt)
        self.say("info", f"Race finished. {len(lt)} laps in {self.race_time:.1f} s "
                         f"of race time. Lap times: {laps_txt}. "
                         f"Distance {self.distance:.2f} m.",
                 lap_times=lt, total_time=self.race_time, distance=self.distance)

    def current_lap(self):
        if not self.lap_timer.started:
            return 0
        return min(self.lap_timer.laps_done + 1, self.cfg["laps"])

    def reset_race(self):
        self.send(0.0, 0.0)
        self.lap_timer.reset()
        self.race_time = 0.0
        self.distance = 0.0
        self.end_replan()
        self.idx = None
        if self.delete_cli.service_is_ready():
            self.delete_cli.call_async(DeleteEntity.Request(name="race_cone"))
        if self.set_state_cli.service_is_ready():
            req = SetEntityState.Request()
            st = EntityState()
            st.name = self.cfg["car"]
            st.pose.position.x, st.pose.position.y = self.grid[0], self.grid[1]
            st.pose.position.z = 0.01
            st.pose.orientation.z = math.sin(self.grid[2] / 2)
            st.pose.orientation.w = math.cos(self.grid[2] / 2)
            st.reference_frame = "world"
            req.state = st
            self.set_state_cli.call_async(req)
            # The next odom message re-maps the odom frame to the grid slot.
            self.odom_offset = None
            self.last_xy = None
            self.say("info", "Car moved back to its grid slot.")
        else:
            self.say("info", "Gazebo state service not ready. Car left where it is.")

    # ----- control loop -----

    def send(self, v, w):
        self.cmd = (v, w)
        t = Twist()
        t.linear.x = float(v)
        t.angular.z = float(w)
        self.cmd_pub.publish(t)

    def pursue(self, v_cap=None):
        cfg = self.cfg
        x, y, yaw = self.pose
        if self.idx is None:
            self.idx = pursuit.nearest_index(self.wps, x, y)
        else:
            self.idx = pursuit.nearest_index(self.wps, x, y, self.idx, cfg["search_window"])
        v, w, k, _ = pursuit.pursuit_command(
            self.wps, x, y, yaw, self.idx, cfg["lookahead"], cfg["v_max"], cfg["v_min"],
            cfg["curvature_gain"], cfg["w_max"])
        if v_cap is not None and v > v_cap:
            w = w * v_cap / v if v > 0 else w
            v = v_cap
        self.kappa = k
        self.send(v, w)

    def start_replan(self):
        cfg = self.cfg
        left, right, r_edge, l_edge = replan.free_beside(
            self.scan_pts, cfg["gap_ahead"], cfg["corridor_half_width"], cfg["gap_cap"])
        if self.replan_side is None:
            self.replan_side = replan.choose_side(left, right)
            kept = ""
        else:
            # Still passing the same obstacle: keep the side picked first.
            kept = " Keeping the side picked first."
        side = self.replan_side
        offset = replan.pass_offset(side, r_edge, l_edge, cfg["replan_clearance"],
                                    cfg["replan_offset_min"], cfg["replan_offset_max"])
        n = len(self.base_wps)
        start = self.idx
        self.wps = replan.shift_waypoints(self.base_wps, start, cfg["replan_points"],
                                          offset, cfg["replan_ramp"])
        self.replan_end = (start + cfg["replan_points"]) % n
        word = "left" if side > 0 else "right"
        self.fire(sm.BLOCKED)
        self.say("info", f"Free space left {left:.2f} m, right {right:.2f} m.{kept} "
                         f"Shifting the next {cfg['replan_points']} waypoints "
                         f"{abs(offset):.2f} m to the {word}.",
                 left_free=left, right_free=right, side=word)

    def end_replan(self):
        self.wps = list(self.base_wps)
        self.replan_end = None
        self.replan_side = None

    def passed_replan(self):
        n = len(self.base_wps)
        # Distance along the list from idx to the end of the shifted stretch.
        ahead = (self.replan_end - self.idx) % n
        return ahead > n // 2 or ahead == 0

    def tick(self):
        now = self.now()
        dt = 0.0 if self.last_tick is None else max(0.0, now - self.last_tick)
        self.last_tick = now
        if self.pose is None or self.scan is None:
            return
        cfg = self.cfg
        st = self.state

        if st in sm.MOVING:
            self.race_time += dt
            crossing = self.lap_timer.update(self.pose[0], self.pose[1], self.race_time)
            if crossing == "start":
                self.say("lap", "Start line crossed. Lap 1 begins.", lap_event="start")
            elif crossing == "lap":
                k = self.lap_timer.laps_done
                lt = self.lap_timer.lap_times[-1]
                self.say("lap", f"Lap {k} done in {lt:.1f} s.", lap_event="lap",
                         lap_done=k, lap_time=lt)
                if k >= cfg["laps"]:
                    self.fire(sm.LAPS_DONE)
                    self.publish_telemetry()
                    return
                self.say("lap", f"Lap {k + 1} begins.", lap_event="begin")

        if st == sm.COUNTDOWN:
            left = cfg["countdown_s"] - (now - self.state_since)
            n = math.ceil(left)
            if left <= 0:
                self.fire(sm.COUNTDOWN_DONE)
                self.say("info", "Go.")
            elif n != self.countdown_said:
                self.countdown_said = n
                self.say("info", f"Countdown {n}.")
            self.send(0.0, 0.0)
        elif st == sm.RACING:
            if self.replan_end is not None and self.passed_replan():
                self.end_replan()
            if self.corridor < cfg["avoid_distance"]:
                self.fire(sm.OBSTACLE)
            else:
                self.pursue()
        elif st == sm.AVOID:
            self.send(0.0, 0.0)
            if self.corridor >= cfg["clear_distance"]:
                self.fire(sm.PATH_CLEAR)
            elif now - self.state_since >= cfg["avoid_hold_s"]:
                self.start_replan()
        elif st == sm.REPLAN:
            close = replan.corridor_distance(self.scan_pts, cfg["replan_stop_half_width"],
                                             cfg["replan_stop_distance"] + 0.01)
            if close < cfg["replan_stop_distance"]:
                self.fire(sm.OBSTACLE, front=close)
            elif self.passed_replan():
                self.end_replan()
                self.fire(sm.PASSED)
            else:
                self.pursue(v_cap=cfg["replan_speed"])
        else:
            self.send(0.0, 0.0)
        if st == sm.IDLE:
            self.countdown_said = None
        self.publish_telemetry()

    # ----- reporting -----

    def publish_telemetry(self):
        x, y, yaw = self.pose
        msg = {
            "t": round(self.now(), 3), "race_t": round(self.race_time, 3),
            "state": self.state, "lap": self.current_lap(),
            "laps_done": self.lap_timer.laps_done,
            "x": round(x, 4), "y": round(y, 4), "yaw": round(yaw, 4),
            "speed": round(self.speed, 4), "cmd_v": round(self.cmd[0], 4),
            "cmd_w": round(self.cmd[1], 4), "curvature": round(self.kappa, 4),
            "front": round(self.front, 3) if math.isfinite(self.front) else None,
            "corridor": round(self.corridor, 3),
            "min_range": round(self.min_r, 3) if math.isfinite(self.min_r) else None,
            "distance": round(self.distance, 3),
            "replanning": self.replan_end is not None,
        }
        self.telem_pub.publish(String(data=json.dumps(msg)))

    def publish_status(self):
        if self.pose is None:
            return
        front = self.front if math.isfinite(self.front) else None
        msg = {"state": self.state, "lap": self.current_lap(), "laps": self.cfg["laps"],
               "speed": round(self.speed, 3), "distance": round(self.distance, 2),
               "front_range": round(front, 2) if front is not None else None,
               "race_time": round(self.race_time, 1)}
        self.status_pub.publish(String(data=json.dumps(msg)))

    def stop(self):
        for _ in range(3):
            self.send(0.0, 0.0)


def raise_interrupt(*_):
    raise KeyboardInterrupt


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, raise_interrupt)
    node = RaceController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.get_logger().info("Shutting down. Sent zero velocity.")
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
