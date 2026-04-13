"""
yahboom_mcu.py
--------------
Hardware abstraction for the Yahboom Raspbot MCU coprocessor.

I2C bus : 1  (GPIO2=SDA / GPIO3=SCL on the 40-pin header)
Address : 0x2B

Register map (verified against official Yahboom Raspbot library):

  0x01  Motor     write [motor_id, dir, speed]
                    motor_id : 0=FL  1=RL  2=FR  3=RR
                    dir      : 0=forward  1=backward
                    speed    : 0-255

  0x02  Servo     write [servo_id, angle]
                    servo_id : 1=pan  2=tilt  (tilt max 100°)
                    angle    : 0-180

  0x03  LED all   write [state, color]
                    state : 0=off  1=on
                    color : 0=red 1=green 2=blue 3=yellow 4=purple 5=cyan 6=white

  0x04  LED one   write [index, state, color]   index: 1-14

  0x05  IR switch write [state]   0=off  1=on

  0x06  Buzzer    write [state]   0=off  1=on

  0x07  Ultrasound write [state]  0=off  1=on

  0x08  LED brightness all    write [R, G, B]   0-255 each

  0x09  LED brightness one    write [index, R, G, B]

  0x0A  Line tracking read    read 1 byte
                    bit3=left1  bit2=left2  bit1=right1  bit0=right2

  0x0C  IR remote read        read 1 byte

  0x1A  Ultrasound low byte   read 1 byte
  0x1B  Ultrasound high byte  read 1 byte
        distance (mm) = (high << 8) | low
"""

import smbus2

_I2C_BUS  = 1
_I2C_ADDR = 0x2B

_REG_MOTOR       = 0x01
_REG_SERVO       = 0x02
_REG_LED_ALL     = 0x03
_REG_LED_ONE     = 0x04
_REG_IR_SW       = 0x05
_REG_BUZZER      = 0x06
_REG_ULTRASOUND  = 0x07
_REG_LED_RGB_ALL = 0x08
_REG_LED_RGB_ONE = 0x09
_REG_TRACKING    = 0x0A
_REG_IR_VAL      = 0x0C
_REG_US_LOW      = 0x1A
_REG_US_HIGH     = 0x1B


class YahboomMCU:
    """Full I2C API for the Yahboom Raspbot MCU coprocessor."""

    # Motor position → MCU motor ID (verified by hardware probing)
    MOTOR_FL = 0
    MOTOR_RL = 1
    MOTOR_FR = 2
    MOTOR_RR = 3

    # LED colors
    RED    = 0
    GREEN  = 1
    BLUE   = 2
    YELLOW = 3
    PURPLE = 4
    CYAN   = 5
    WHITE  = 6

    def __init__(self, bus: int = _I2C_BUS, addr: int = _I2C_ADDR):
        self._addr = addr
        self._bus  = smbus2.SMBus(bus)

    # ------------------------------------------------------------------
    # Internal write helpers
    # ------------------------------------------------------------------
    def _write(self, reg: int, data: list[int]) -> None:
        self._bus.write_i2c_block_data(self._addr, reg, data)

    def _write_byte(self, reg: int, value: int) -> None:
        self._bus.write_byte_data(self._addr, reg, value)

    def _read(self, reg: int, length: int) -> list[int]:
        return self._bus.read_i2c_block_data(self._addr, reg, length)

    # ------------------------------------------------------------------
    # Motors
    # ------------------------------------------------------------------
    def set_motor(self, motor_id: int, speed: int) -> None:
        """
        Control one motor.

        :param motor_id: MOTOR_FL / MOTOR_RL / MOTOR_FR / MOTOR_RR
        :param speed:    -255 (full reverse) … 0 (stop) … +255 (full forward)
        """
        speed   = max(-255, min(255, speed))
        dir_    = 0 if speed >= 0 else 1     # 0=forward  1=backward
        self._write(_REG_MOTOR, [motor_id, dir_, abs(speed)])

    def stop_all_motors(self) -> None:
        for mid in [self.MOTOR_FL, self.MOTOR_RL, self.MOTOR_FR, self.MOTOR_RR]:
            self._write(_REG_MOTOR, [mid, 0, 0])

    # ------------------------------------------------------------------
    # Servos
    # ------------------------------------------------------------------
    def set_servo(self, servo_id: int, angle: int) -> None:
        """
        :param servo_id: 1=pan  2=tilt
        :param angle:    0-180° (tilt capped at 100°)
        """
        angle = max(0, min(180, angle))
        if servo_id == 2:
            angle = min(angle, 100)
        self._write(_REG_SERVO, [servo_id, angle])

    # ------------------------------------------------------------------
    # LED light bar (all 14 LEDs — color mode)
    # ------------------------------------------------------------------
    def led_all(self, state: int, color: int) -> None:
        """
        :param state: 0=off  1=on
        :param color: RED/GREEN/BLUE/YELLOW/PURPLE/CYAN/WHITE (0-6)
        """
        state = max(0, min(1, state))
        color = max(0, min(6, color))
        self._write(_REG_LED_ALL, [state, color])

    def led_off(self) -> None:
        self.led_all(0, 0)

    def led_one(self, index: int, state: int, color: int) -> None:
        """
        :param index: 1-14
        :param state: 0=off  1=on
        :param color: 0-6
        """
        state = max(0, min(1, state))
        color = max(0, min(6, color))
        self._write(_REG_LED_ONE, [index, state, color])

    # ------------------------------------------------------------------
    # LED light bar (brightness / RGB mode)
    # ------------------------------------------------------------------
    def led_rgb_all(self, r: int, g: int, b: int) -> None:
        """Set brightness of all 14 LEDs via RGB. 0-255 each channel."""
        r, g, b = min(255, r), min(255, g), min(255, b)
        self._write(_REG_LED_RGB_ALL, [r, g, b])

    def led_rgb_one(self, index: int, r: int, g: int, b: int) -> None:
        """Set brightness of a single LED (index 1-14) via RGB."""
        r, g, b = min(255, r), min(255, g), min(255, b)
        self._write(_REG_LED_RGB_ONE, [index, r, g, b])

    # ------------------------------------------------------------------
    # Buzzer
    # ------------------------------------------------------------------
    def buzzer(self, state: int) -> None:
        """state: 0=off  1=on"""
        self._write(_REG_BUZZER, [max(0, min(1, state))])

    # ------------------------------------------------------------------
    # IR obstacle avoidance
    # ------------------------------------------------------------------
    def ir_switch(self, state: int) -> None:
        """Enable / disable IR obstacle sensors. state: 0=off 1=on"""
        self._write(_REG_IR_SW, [max(0, min(1, state))])

    # ------------------------------------------------------------------
    # Ultrasonic
    # ------------------------------------------------------------------
    def ultrasound_switch(self, state: int) -> None:
        """Enable / disable ultrasonic sensor. state: 0=off 1=on"""
        self._write(_REG_ULTRASOUND, [max(0, min(1, state))])

    def read_distance_mm(self) -> int:
        """
        Returns distance in mm.
        Call ultrasound_switch(1) and wait ~100ms before reading.
        """
        low  = self._read(_REG_US_LOW,  1)[0]
        high = self._read(_REG_US_HIGH, 1)[0]
        return (high << 8) | low

    # ------------------------------------------------------------------
    # Line tracking
    # ------------------------------------------------------------------
    def read_tracking(self) -> dict:
        """
        Returns dict with boolean values for each sensor:
          { 'left1': bool, 'left2': bool, 'right1': bool, 'right2': bool }
        Sensor is True when detecting a line (dark surface).
        """
        raw = self._read(_REG_TRACKING, 1)[0]
        return {
            'left1':  bool((raw >> 3) & 0x01),
            'left2':  bool((raw >> 2) & 0x01),
            'right1': bool((raw >> 1) & 0x01),
            'right2': bool((raw     ) & 0x01),
        }

    # ------------------------------------------------------------------
    # IR remote
    # ------------------------------------------------------------------
    def read_ir_remote(self) -> int:
        """Returns the last IR key code received (0x00 = none)."""
        return self._read(_REG_IR_VAL, 1)[0]

    # ------------------------------------------------------------------
    def close(self) -> None:
        self.stop_all_motors()
        self.led_off()
        self._bus.close()
