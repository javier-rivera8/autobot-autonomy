#!/usr/bin/env python3
"""
tools/test_motors.py
--------------------
Prueba rápida de los 4 motores usando YahboomMCU.
Ejecutar directamente en la Raspberry Pi (fuera del container).

Uso:
    python3 tools/test_motors.py
"""
import sys, time
sys.path.insert(0, 'src/autobot_drivers')

from autobot_drivers.yahboom_mcu import YahboomMCU

mcu = YahboomMCU()

MOTORS = [
    (YahboomMCU.MOTOR_FL, 'FL (ID=0)'),
    (YahboomMCU.MOTOR_FR, 'FR (ID=2)'),
    (YahboomMCU.MOTOR_RL, 'RL (ID=1)'),
    (YahboomMCU.MOTOR_RR, 'RR (ID=3)'),
]

print('=== Test de motores — robot levantado ===\n')
try:
    for mid, label in MOTORS:
        print(f'{label} → adelante 150/255')
        mcu.set_motor(mid,  150)
        time.sleep(1.5)
        print(f'{label} → atrás 150/255')
        mcu.set_motor(mid, -150)
        time.sleep(1.5)
        mcu.set_motor(mid, 0)
        time.sleep(0.3)

    print('\nTodos adelante 200/255 ...')
    for mid, _ in MOTORS:
        mcu.set_motor(mid, 200)
    time.sleep(2)
    mcu.stop_all_motors()
    print('Stop')

finally:
    mcu.close()
    print('Fin')
