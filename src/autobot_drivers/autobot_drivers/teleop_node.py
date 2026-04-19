#!/usr/bin/env python3
"""
teleop_node.py
--------------
Keyboard teleop for the Yahboom Raspbot — drives motors, servos, buzzer & LEDs.

Controls:
  Movement (motors):
    W / ↑   Forward          S / ↓   Backward
    A / ←   Turn left        D / →   Turn right
    Q       Forward-left     E       Forward-right
    SPACE   Stop

  Speed:
    +/=     Speed up         -       Speed down

  Servo (pan/tilt camera):
    I       Tilt up          K       Tilt down
    J       Pan left         L       Pan right
    O       Center servos

  Buzzer:
    B       Toggle buzzer

  LED light bar:
    1-7     Set color (red/green/blue/yellow/purple/cyan/white)
    0       LEDs off
    R/G     Increase/decrease RGB red channel
    T/H     Increase/decrease RGB green channel
    Y/N     Increase/decrease RGB blue channel

  Quit:
    Ctrl-C  or  X
"""

import select
import sys
import termios
import threading
import time
import tty

import rclpy
from rclpy.node import Node

from autobot_drivers.yahboom_mcu import YahboomMCU

# ---- Key constants ---------------------------------------------------------
# Arrow keys send escape sequences: ESC [ A/B/C/D
_ARROW_PREFIX = '\x1b'

_HELP = """
╔══════════════════════════════════════════════════════════╗
║                AUTOBOT KEYBOARD TELEOP                  ║
╠══════════════════════════════════════════════════════════╣
║  MOVEMENT (hold)   SERVO            LED BAR             ║
║  W / ↑  Fwd        I  Tilt up       1-7 Color preset   ║
║  S / ↓  Back       K  Tilt down     0   LEDs off       ║
║  A / ←  Turn L     J  Pan left      R/G  Red ±         ║
║  D / →  Turn R     L  Pan right     T/H  Green ±       ║
║  Q      Fwd+L      O  Center        Y/N  Blue ±        ║
║  E      Fwd+R                                          ║
║  SPACE  Stop       BUZZER           SPEED               ║
║                    B  Toggle        +  Speed up         ║
║  X / Ctrl-C  Quit                   -  Speed down      ║
╚══════════════════════════════════════════════════════════╝
"""


def _getch(timeout: float = 0.15) -> str:
    """Read a single keypress with timeout. Returns '' on timeout."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if not rlist:
            return ''
        ch = sys.stdin.read(1)
        # Handle escape sequences (arrow keys)
        if ch == _ARROW_PREFIX:
            rlist2, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not rlist2:
                return ''
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                rlist3, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not rlist3:
                    return ''
                ch3 = sys.stdin.read(1)
                return {
                    'A': 'UP', 'B': 'DOWN',
                    'C': 'RIGHT', 'D': 'LEFT',
                }.get(ch3, '')
            return ''
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


class TeleopNode(Node):

    SPEED_STEP     = 25
    SERVO_STEP     = 5
    RGB_STEP       = 30
    PAN_CENTER     = 90
    TILT_CENTER    = 50
    PAN_MIN, PAN_MAX   = 0, 180
    TILT_MIN, TILT_MAX = 0, 100

    def __init__(self):
        super().__init__('teleop')

        try:
            self._mcu = YahboomMCU()
            self.get_logger().info('YahboomMCU: I2C open OK')
        except Exception as e:
            self.get_logger().error(f'Cannot open MCU: {e}')
            raise

        self._speed      = 150   # current motor speed (0-255)
        self._pan_angle  = self.PAN_CENTER
        self._tilt_angle = self.TILT_CENTER
        self._buzzer_on  = False
        self._rgb        = [0, 0, 0]

        # Center servos on startup
        self._mcu.set_servo(1, self._pan_angle)
        self._mcu.set_servo(2, self._tilt_angle)

        self.get_logger().info('teleop node ready')
        self._moving = False  # track whether motors are currently running

    # ------------------------------------------------------------------
    # Motor helpers
    # ------------------------------------------------------------------
    def _drive(self, left: int, right: int) -> None:
        self._mcu.set_motor(YahboomMCU.MOTOR_FL, left)
        self._mcu.set_motor(YahboomMCU.MOTOR_RL, left)
        self._mcu.set_motor(YahboomMCU.MOTOR_FR, right)
        self._mcu.set_motor(YahboomMCU.MOTOR_RR, right)

    def _stop(self) -> None:
        self._mcu.stop_all_motors()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        print(_HELP)
        print(f'  Speed: {self._speed}/255')

        try:
            while True:
                key = _getch()

                # No key within timeout → stop motors if moving
                if not key:
                    if self._moving:
                        self._stop()
                        self._moving = False
                        self._status('STOP')
                    continue

                k = key.lower() if len(key) == 1 else key

                # ----- Movement -----------------------------------------
                if k in ('w', 'UP'):
                    self._drive(self._speed, self._speed)
                    self._moving = True
                    self._status('Forward')
                elif k in ('s', 'DOWN'):
                    self._drive(-self._speed, -self._speed)
                    self._moving = True
                    self._status('Backward')
                elif k in ('a', 'LEFT'):
                    self._drive(-self._speed, self._speed)
                    self._moving = True
                    self._status('Turn left')
                elif k in ('d', 'RIGHT'):
                    self._drive(self._speed, -self._speed)
                    self._moving = True
                    self._status('Turn right')
                elif k == 'q':
                    self._drive(self._speed // 2, self._speed)
                    self._moving = True
                    self._status('Forward-left')
                elif k == 'e':
                    self._drive(self._speed, self._speed // 2)
                    self._moving = True
                    self._status('Forward-right')
                elif k == ' ':
                    self._stop()
                    self._moving = False
                    self._status('STOP')

                # ----- Speed -------------------------------------------
                elif key in ('+', '='):
                    self._speed = min(255, self._speed + self.SPEED_STEP)
                    self._status(f'Speed: {self._speed}/255')
                elif key == '-':
                    self._speed = max(0, self._speed - self.SPEED_STEP)
                    self._status(f'Speed: {self._speed}/255')

                # ----- Servo -------------------------------------------
                elif k == 'i':
                    self._tilt_angle = min(self.TILT_MAX,
                                           self._tilt_angle + self.SERVO_STEP)
                    self._mcu.set_servo(2, self._tilt_angle)
                    self._status(f'Tilt: {self._tilt_angle}°')
                elif k == 'k':
                    self._tilt_angle = max(self.TILT_MIN,
                                           self._tilt_angle - self.SERVO_STEP)
                    self._mcu.set_servo(2, self._tilt_angle)
                    self._status(f'Tilt: {self._tilt_angle}°')
                elif k == 'j':
                    self._pan_angle = min(self.PAN_MAX,
                                          self._pan_angle + self.SERVO_STEP)
                    self._mcu.set_servo(1, self._pan_angle)
                    self._status(f'Pan: {self._pan_angle}°')
                elif k == 'l':
                    self._pan_angle = max(self.PAN_MIN,
                                          self._pan_angle - self.SERVO_STEP)
                    self._mcu.set_servo(1, self._pan_angle)
                    self._status(f'Pan: {self._pan_angle}°')
                elif k == 'o':
                    self._pan_angle = self.PAN_CENTER
                    self._tilt_angle = self.TILT_CENTER
                    self._mcu.set_servo(1, self._pan_angle)
                    self._mcu.set_servo(2, self._tilt_angle)
                    self._status('Servos centered')

                # ----- Buzzer ------------------------------------------
                elif k == 'b':
                    self._buzzer_on = not self._buzzer_on
                    self._mcu.buzzer(1 if self._buzzer_on else 0)
                    self._status(
                        f'Buzzer {"ON" if self._buzzer_on else "OFF"}')

                # ----- LED color presets (1-7, 0=off) ------------------
                elif key == '0':
                    self._mcu.led_off()
                    self._rgb = [0, 0, 0]
                    self._status('LEDs OFF')
                elif key == '1':
                    self._mcu.led_all(1, YahboomMCU.RED)
                    self._status('LEDs: RED')
                elif key == '2':
                    self._mcu.led_all(1, YahboomMCU.GREEN)
                    self._status('LEDs: GREEN')
                elif key == '3':
                    self._mcu.led_all(1, YahboomMCU.BLUE)
                    self._status('LEDs: BLUE')
                elif key == '4':
                    self._mcu.led_all(1, YahboomMCU.YELLOW)
                    self._status('LEDs: YELLOW')
                elif key == '5':
                    self._mcu.led_all(1, YahboomMCU.PURPLE)
                    self._status('LEDs: PURPLE')
                elif key == '6':
                    self._mcu.led_all(1, YahboomMCU.CYAN)
                    self._status('LEDs: CYAN')
                elif key == '7':
                    self._mcu.led_all(1, YahboomMCU.WHITE)
                    self._status('LEDs: WHITE')

                # ----- LED RGB fine control ----------------------------
                elif k == 'r':
                    self._rgb[0] = min(255, self._rgb[0] + self.RGB_STEP)
                    self._set_rgb()
                elif k == 'g':
                    self._rgb[0] = max(0, self._rgb[0] - self.RGB_STEP)
                    self._set_rgb()
                elif k == 't':
                    self._rgb[1] = min(255, self._rgb[1] + self.RGB_STEP)
                    self._set_rgb()
                elif k == 'h':
                    self._rgb[1] = max(0, self._rgb[1] - self.RGB_STEP)
                    self._set_rgb()
                elif k == 'y':
                    self._rgb[2] = min(255, self._rgb[2] + self.RGB_STEP)
                    self._set_rgb()
                elif k == 'n':
                    self._rgb[2] = max(0, self._rgb[2] - self.RGB_STEP)
                    self._set_rgb()

                # ----- Quit -------------------------------------------
                elif k == 'x' or key == '\x03':  # Ctrl-C
                    break

        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self._shutdown()

    def _set_rgb(self) -> None:
        r, g, b = self._rgb
        self._mcu.led_rgb_all(r, g, b)
        self._status(f'RGB: ({r}, {g}, {b})')

    def _status(self, msg: str) -> None:
        # \r + clear line so we overwrite in-place
        print(f'\r\033[K  {msg}', end='', flush=True)

    def _shutdown(self) -> None:
        print('\n\nShutting down...')
        self._mcu.stop_all_motors()
        self._mcu.buzzer(0)
        self._mcu.led_off()
        self._mcu.set_servo(1, self.PAN_CENTER)
        self._mcu.set_servo(2, self.TILT_CENTER)
        self._mcu.close()


def main(args=None):
    rclpy.init(args=args)
    node = TeleopNode()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
