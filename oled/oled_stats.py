#!/usr/bin/env python3
"""
oled_stats.py — Show system stats on the SSD1306 OLED (128×32)
Runs standalone on the Raspberry Pi (no Docker, no ROS).

Displays:
  Line 1: CPU usage % + temperature °C
  Line 2: RAM usage %
  Line 3: IP address

Install deps:
  sudo pip3 install --break-system-packages luma.oled psutil

Hardware:
  SSD1306 128×32, I2C bus 1, address 0x3C
"""

import subprocess
import time

import psutil
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

I2C_BUS  = 1
I2C_ADDR = 0x3C
UPDATE_INTERVAL = 2  # seconds


def get_cpu_temp() -> float:
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return 0.0


def get_ip() -> str:
    try:
        out = subprocess.check_output(
            ['hostname', '-I'], text=True, timeout=2)
        parts = out.strip().split()
        return parts[0] if parts else 'N/A'
    except Exception:
        return 'N/A'


def main() -> None:
    serial = i2c(port=I2C_BUS, address=I2C_ADDR)
    oled = ssd1306(serial, width=128, height=32)

    try:
        font = ImageFont.truetype(
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 10)
    except Exception:
        font = ImageFont.load_default()

    try:
        while True:
            cpu  = psutil.cpu_percent(interval=None)
            temp = get_cpu_temp()
            ram  = psutil.virtual_memory().percent
            ip   = get_ip()

            with canvas(oled) as draw:
                draw.text((0,  0), f'CPU:{cpu:5.1f}%  {temp:4.1f}C',
                          fill='white', font=font)
                draw.text((0, 11), f'RAM:{ram:5.1f}%',
                          fill='white', font=font)
                draw.text((0, 22), f'{ip}',
                          fill='white', font=font)

            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        oled.hide()


if __name__ == '__main__':
    main()
