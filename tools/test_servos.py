#!/usr/bin/env python3
"""
tools/test_servos.py
--------------------
Prueba de los 2 servos (pan y tilt) usando YahboomMCU.

Uso:
    python3 tools/test_servos.py
"""
import sys, time
sys.path.insert(0, 'src/autobot_drivers')

from autobot_drivers.yahboom_mcu import YahboomMCU

mcu = YahboomMCU()

print('=== Test de servos ===\n')
print('Servo 1 = pan (horizontal)')
print('Servo 2 = tilt (vertical, max 100°)\n')

try:
    for servo_id, label, max_angle in [(1, 'Pan',  180), (2, 'Tilt', 100)]:
        print(f'{label} (ID={servo_id})')
        for angle in [90, 0, max_angle, 90]:
            print(f'  → {angle}°')
            mcu.set_servo(servo_id, angle)
            time.sleep(1.5)

finally:
    mcu.set_servo(1, 90)
    mcu.set_servo(2, 90)
    mcu.close()
    print('Fin — servos centrados')
