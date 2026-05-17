#!/usr/bin/env python3
"""
bottle_hunt_mission_node.py
---------------------------
Autonomous mission:
  1. Rotate until a bottle is detected.
  2. Center the bottle in the camera image.
  3. Approach while centered.
  4. Stop when the bottle is close enough by image size or ultrasonic range.

Inputs:
  /bottle_target  std_msgs/Float32MultiArray
      [visible, center_x, center_y, area, confidence]

Output:
  /cmd_vel        geometry_msgs/Twist
"""

import math
import time
from enum import Enum

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

from autobot_drivers.yahboom_mcu import YahboomMCU


class MissionState(Enum):
    SEARCHING = 'searching'
    TRACKING = 'tracking'
    FOUND = 'found'


class BottleHuntMissionNode(Node):

    def __init__(self):
        super().__init__('bottle_hunt_mission')

        self.declare_parameter('target_topic', '/bottle_target')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('control_hz', 10.0)
        self.declare_parameter('search_angular_speed', 0.45)
        self.declare_parameter('max_linear_speed', 0.18)
        self.declare_parameter('max_angular_speed', 0.90)
        self.declare_parameter('angular_kp', 1.60)
        self.declare_parameter('center_tolerance', 0.08)
        self.declare_parameter('desired_area', 0.16)
        self.declare_parameter('slow_area', 0.06)
        self.declare_parameter('lost_timeout', 0.80)
        self.declare_parameter('use_ultrasonic', True)
        self.declare_parameter('ultrasonic_hz', 5.0)
        self.declare_parameter('stop_distance_m', 0.28)
        self.declare_parameter('slow_distance_m', 0.55)
        self.declare_parameter('min_valid_distance_m', 0.03)
        self.declare_parameter('max_valid_distance_m', 4.00)

        self._target_topic = self.get_parameter('target_topic').value
        self._cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self._control_hz = float(self.get_parameter('control_hz').value)
        self._search_wz = float(
            self.get_parameter('search_angular_speed').value)
        self._max_vx = float(self.get_parameter('max_linear_speed').value)
        self._max_wz = float(self.get_parameter('max_angular_speed').value)
        self._angular_kp = float(self.get_parameter('angular_kp').value)
        self._center_tolerance = float(
            self.get_parameter('center_tolerance').value)
        self._desired_area = float(self.get_parameter('desired_area').value)
        self._slow_area = float(self.get_parameter('slow_area').value)
        self._lost_timeout = float(self.get_parameter('lost_timeout').value)
        self._use_ultrasonic = bool(
            self.get_parameter('use_ultrasonic').value)
        self._ultrasonic_period = 1.0 / max(
            0.1, float(self.get_parameter('ultrasonic_hz').value))
        self._stop_distance = float(
            self.get_parameter('stop_distance_m').value)
        self._slow_distance = float(
            self.get_parameter('slow_distance_m').value)
        self._min_valid_distance = float(
            self.get_parameter('min_valid_distance_m').value)
        self._max_valid_distance = float(
            self.get_parameter('max_valid_distance_m').value)

        self._state = MissionState.SEARCHING
        self._last_target_time = -math.inf
        self._last_ultrasonic_time = -math.inf
        self._distance_m = math.inf
        self._target_center_x = 0.5
        self._target_area = 0.0
        self._target_confidence = 0.0
        self._found_announced = False

        self._mcu = None
        if self._use_ultrasonic:
            try:
                self._mcu = YahboomMCU()
                self._mcu.ultrasound_switch(1)
                self.get_logger().info('Ultrasonic sensor enabled')
            except Exception as exc:
                self._mcu = None
                self.get_logger().warn(
                    f'Ultrasonic unavailable: {exc}; using camera only')

        self._cmd_pub = self.create_publisher(Twist, self._cmd_vel_topic, 10)
        self._target_sub = self.create_subscription(
            Float32MultiArray,
            self._target_topic,
            self._target_cb,
            10,
        )

        self._timer = self.create_timer(
            1.0 / max(1.0, self._control_hz), self._control_cb)

        self.get_logger().info(
            'bottle_hunt mission ready: search -> center -> approach -> stop')

    def _target_cb(self, msg: Float32MultiArray) -> None:
        if len(msg.data) < 5:
            return

        visible, center_x, _center_y, area, confidence = msg.data[:5]
        if visible < 0.5:
            return

        self._target_center_x = max(0.0, min(1.0, float(center_x)))
        self._target_area = max(0.0, float(area))
        self._target_confidence = max(0.0, float(confidence))
        self._last_target_time = self._now()

    def _control_cb(self) -> None:
        now = self._now()
        self._update_ultrasonic(now)

        target_visible = (now - self._last_target_time) <= self._lost_timeout
        close_by_image = (
            target_visible and self._target_area >= self._desired_area)
        close_by_range = (
            target_visible and self._distance_m <= self._stop_distance)

        if self._state is MissionState.FOUND:
            self._publish_stop()
            return

        if close_by_image or close_by_range:
            self._set_state(MissionState.FOUND)
            self._publish_stop()
            self._signal_found()
            return

        if not target_visible:
            self._set_state(MissionState.SEARCHING)
            self._publish_cmd(0.0, self._search_wz)
            return

        self._set_state(MissionState.TRACKING)
        error = self._target_center_x - 0.5
        angular = max(
            -self._max_wz,
            min(self._max_wz, -self._angular_kp * error),
        )

        linear = 0.0
        if abs(error) <= self._center_tolerance:
            linear = self._approach_speed_from_image()
            linear = self._limit_speed_from_ultrasonic(linear)

        self._publish_cmd(linear, angular)

    def _approach_speed_from_image(self) -> float:
        if self._target_area >= self._desired_area:
            return 0.0
        if self._target_area <= self._slow_area:
            return self._max_vx

        span = max(0.001, self._desired_area - self._slow_area)
        ratio = (self._desired_area - self._target_area) / span
        return max(0.05, min(self._max_vx, self._max_vx * ratio))

    def _limit_speed_from_ultrasonic(self, linear: float) -> float:
        if not math.isfinite(self._distance_m):
            return linear
        if self._distance_m <= self._stop_distance:
            return 0.0
        if self._distance_m >= self._slow_distance:
            return linear

        span = max(0.001, self._slow_distance - self._stop_distance)
        ratio = (self._distance_m - self._stop_distance) / span
        return min(linear, max(0.04, self._max_vx * ratio))

    def _update_ultrasonic(self, now: float) -> None:
        if self._mcu is None:
            return
        if now - self._last_ultrasonic_time < self._ultrasonic_period:
            return

        self._last_ultrasonic_time = now
        try:
            distance_m = self._mcu.read_distance_mm() / 1000.0
        except Exception as exc:
            self.get_logger().warn(f'Ultrasonic read failed: {exc}')
            self._distance_m = math.inf
            return

        if self._min_valid_distance <= distance_m <= self._max_valid_distance:
            self._distance_m = distance_m
        else:
            self._distance_m = math.inf

    def _signal_found(self) -> None:
        if self._found_announced:
            return
        self._found_announced = True
        self.get_logger().info(
            'Bottle found; stopping '
            f'(area={self._target_area:.2f}, distance={self._distance_text()})')

        if self._mcu is None:
            return

        try:
            self._mcu.buzzer(1)
            time.sleep(0.20)
            self._mcu.buzzer(0)
        except Exception as exc:
            self.get_logger().warn(f'Buzzer signal failed: {exc}')

    def _set_state(self, state: MissionState) -> None:
        if state is self._state:
            return
        self._state = state
        self.get_logger().info(f'Mission state: {state.value}')

    def _publish_cmd(self, linear_x: float, angular_z: float) -> None:
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self._cmd_pub.publish(msg)

    def _publish_stop(self) -> None:
        self._publish_cmd(0.0, 0.0)

    def _distance_text(self) -> str:
        if math.isfinite(self._distance_m):
            return f'{self._distance_m:.2f}m'
        return 'n/a'

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def destroy_node(self) -> None:
        self._publish_stop()
        if self._mcu:
            try:
                self._mcu.buzzer(0)
                self._mcu.ultrasound_switch(0)
                self._mcu.close()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BottleHuntMissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
