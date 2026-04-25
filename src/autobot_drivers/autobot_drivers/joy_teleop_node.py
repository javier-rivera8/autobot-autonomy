#!/usr/bin/env python3
"""
joy_teleop_node.py
------------------
Xbox controller teleop for the Yahboom Raspbot.

Requires: ros-jazzy-joy (publishes /joy)

Controller mapping (Xbox layout):
  Left stick Y          Forward / Backward
  Left stick X          Turn left / right
  Right stick X         Pan servo
  Right stick Y         Tilt servo
  RT (axis 5)           Strafe right (mecanum)
  LT (axis 2)           Strafe left  (mecanum)
  A button (0)          Toggle buzzer
  B button (1)          LEDs red
  X button (2)          LEDs blue
  Y button (3)          LEDs green
  LB (4)                LEDs purple
  RB (5)                LEDs white
  Back/Select (6)       LEDs off
  Start (7)             Center servos
  D-pad up/down         Tilt servo nudge
  D-pad left/right      Pan servo nudge

Topics:
  Subscribed : /joy (sensor_msgs/Joy)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

from autobot_drivers.yahboom_mcu import YahboomMCU


class JoyTeleopNode(Node):

    # Xbox button indices (may vary — evdev/xpad standard)
    BTN_A     = 0
    BTN_B     = 1
    BTN_X     = 2
    BTN_Y     = 3
    BTN_LB    = 4
    BTN_RB    = 5
    BTN_BACK  = 6
    BTN_START = 7

    # Xbox axis indices
    AXIS_LEFT_X   = 0   # left stick horizontal  (-1 left, +1 right)
    AXIS_LEFT_Y   = 1   # left stick vertical    (-1 down, +1 up ... inverted)
    AXIS_LT       = 2   # left trigger   (+1 released, -1 fully pressed)
    AXIS_RIGHT_X  = 3   # right stick horizontal
    AXIS_RIGHT_Y  = 4   # right stick vertical
    AXIS_RT       = 5   # right trigger  (+1 released, -1 fully pressed)
    AXIS_DPAD_X   = 6   # d-pad horizontal (-1 left, +1 right)
    AXIS_DPAD_Y   = 7   # d-pad vertical   (-1 down, +1 up)

    # Servo limits
    PAN_CENTER, TILT_CENTER = 90, 50
    PAN_MIN, PAN_MAX = 0, 180
    TILT_MIN, TILT_MAX = 0, 100

    DEADZONE = 0.25
    SERVO_DEADZONE = 0.20   # threshold to ignore resting-axis drift
    SERVO_RATE = 5.0     # max degrees per joy callback (rate-limited absolute)
    DPAD_SERVO_STEP = 5  # degrees per d-pad press

    def __init__(self):
        super().__init__('joy_teleop')

        self.declare_parameter('max_speed', 200)
        self._max_speed = self.get_parameter('max_speed').value

        try:
            self._mcu = YahboomMCU()
            self.get_logger().info('YahboomMCU: I2C open OK')
        except Exception as e:
            self.get_logger().error(f'Cannot open MCU: {e}')
            raise

        self._buzzer_on  = False
        self._pan_angle  = self.PAN_CENTER
        self._tilt_angle = self.TILT_CENTER
        self._prev_buttons = []

        # Center servos
        self._mcu.set_servo(1, self._pan_angle)
        self._mcu.set_servo(2, self._tilt_angle)

        self._sub = self.create_subscription(Joy, '/joy', self._joy_cb, 10)

        self.get_logger().info(
            f'joy_teleop ready (max_speed={self._max_speed})')

    # ------------------------------------------------------------------
    def _joy_cb(self, msg: Joy) -> None:
        axes = msg.axes
        buttons = msg.buttons

        # Need at least 6 axes (left stick + triggers + right stick).
        # Dpad-as-axis (indices 6-7) is optional — some controllers expose dpad as buttons.
        if len(axes) < 6 or len(buttons) < 8:
            self.get_logger().warn(
                f'Joy msg too small: {len(axes)} axes / {len(buttons)} buttons '
                '(need ≥6 axes, ≥8 buttons) — skipping',
                throttle_duration_sec=5.0)
            return

        # --- Detect button edges (pressed this frame) ---
        pressed = set()
        if self._prev_buttons:
            for i in range(min(len(buttons), len(self._prev_buttons))):
                if buttons[i] == 1 and self._prev_buttons[i] == 0:
                    pressed.add(i)
        self._prev_buttons = list(buttons)

        # --- Motors (left stick = fwd/turn, triggers = strafe) ----------
        # Triggers: axis +1 released → -1 fully pressed → remap to 0..1
        lt_val = (1.0 - axes[self.AXIS_LT]) / 2.0  # 0=released  1=fully pressed
        rt_val = (1.0 - axes[self.AXIS_RT]) / 2.0  # 0=released  1=fully pressed
        strafe = rt_val - lt_val  # +1 = strafe right, -1 = strafe left

        if abs(strafe) > 0.1:
            # Mecanum strafing: FL+/RR+ forward, RL-/FR- backward (strafe right)
            # Invert sign to strafe left. If direction is wrong, swap MOTOR_FL/RR signs.
            spd = max(-255, min(255, int(strafe * self._max_speed)))
            self._mcu.set_motor(YahboomMCU.MOTOR_FL,  spd)
            self._mcu.set_motor(YahboomMCU.MOTOR_RL, -spd)
            self._mcu.set_motor(YahboomMCU.MOTOR_FR, -spd)
            self._mcu.set_motor(YahboomMCU.MOTOR_RR,  spd)
        else:
            # Normal forward / turn (left stick)
            fwd  =  axes[self.AXIS_LEFT_Y]
            turn =  axes[self.AXIS_LEFT_X]

            if abs(fwd)  < self.DEADZONE: fwd  = 0.0
            if abs(turn) < self.DEADZONE: turn = 0.0

            left  = max(-255, min(255, int((fwd - turn) * self._max_speed)))
            right = max(-255, min(255, int((fwd + turn) * self._max_speed)))

            self._mcu.set_motor(YahboomMCU.MOTOR_FL, left)
            self._mcu.set_motor(YahboomMCU.MOTOR_RL, left)
            self._mcu.set_motor(YahboomMCU.MOTOR_FR, right)
            self._mcu.set_motor(YahboomMCU.MOTOR_RR, right)

        # --- Servos (right stick Y = tilt only, pan fixed at center) ------
        rs_y = -axes[self.AXIS_RIGHT_Y]

        self.get_logger().debug(
            f'right_stick  rs_y={rs_y:+.3f}  tilt={self._tilt_angle:.1f}°')

        # Rate mode: stick deflection increments tilt; holds when released.
        if abs(rs_y) > self.SERVO_DEADZONE:
            self._tilt_angle += rs_y * self.SERVO_RATE

        # D-pad nudge vertical only (optional — only if controller exposes dpad as axes)
        dpad_y = axes[self.AXIS_DPAD_Y] if len(axes) > self.AXIS_DPAD_Y else 0.0
        if abs(dpad_y) > 0.5:
            self._tilt_angle += self.DPAD_SERVO_STEP * (1 if dpad_y > 0 else -1)

        # Clamp and send — pan always at center
        self._tilt_angle = max(self.TILT_MIN, min(self.TILT_MAX, self._tilt_angle))
        self._mcu.set_servo(1, self.PAN_CENTER)
        self._mcu.set_servo(2, int(self._tilt_angle))

        # --- Start → center servos ------------------------------------
        if self.BTN_START in pressed:
            self._pan_angle = self.PAN_CENTER
            self._tilt_angle = self.TILT_CENTER
            self._mcu.set_servo(1, self._pan_angle)
            self._mcu.set_servo(2, self._tilt_angle)
            self.get_logger().info('Servos centered')

        # --- Buzzer (A) -----------------------------------------------
        if self.BTN_A in pressed:
            self._buzzer_on = not self._buzzer_on
            self._mcu.buzzer(1 if self._buzzer_on else 0)
            self.get_logger().info(
                f'Buzzer {"ON" if self._buzzer_on else "OFF"}')

        # --- LEDs ------------------------------------------------------
        if self.BTN_B in pressed:
            self._mcu.led_all(1, YahboomMCU.RED)
            self.get_logger().info('LEDs: RED')
        elif self.BTN_X in pressed:
            self._mcu.led_all(1, YahboomMCU.BLUE)
            self.get_logger().info('LEDs: BLUE')
        elif self.BTN_Y in pressed:
            self._mcu.led_all(1, YahboomMCU.GREEN)
            self.get_logger().info('LEDs: GREEN')
        elif self.BTN_LB in pressed:
            self._mcu.led_all(1, YahboomMCU.PURPLE)
            self.get_logger().info('LEDs: PURPLE')
        elif self.BTN_RB in pressed:
            self._mcu.led_all(1, YahboomMCU.WHITE)
            self.get_logger().info('LEDs: WHITE')
        elif self.BTN_BACK in pressed:
            self._mcu.led_off()
            self.get_logger().info('LEDs: OFF')

    # ------------------------------------------------------------------
    def destroy_node(self) -> None:
        if self._mcu:
            self._mcu.stop_all_motors()
            self._mcu.buzzer(0)
            self._mcu.led_off()
            self._mcu.set_servo(1, self.PAN_CENTER)
            self._mcu.set_servo(2, self.TILT_CENTER)
            self._mcu.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JoyTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
