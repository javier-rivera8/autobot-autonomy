#!/usr/bin/env python3
"""
tools/test_leds.py
------------------
Prueba del light bar de 14 LEDs WS2812 usando YahboomMCU.

Uso:
    python3 tools/test_leds.py
"""
import sys, time
sys.path.insert(0, 'src/autobot_drivers')

from autobot_drivers.yahboom_mcu import YahboomMCU

mcu = YahboomMCU()

COLORS = [
    (YahboomMCU.RED,    'Rojo'),
    (YahboomMCU.GREEN,  'Verde'),
    (YahboomMCU.BLUE,   'Azul'),
    (YahboomMCU.YELLOW, 'Amarillo'),
    (YahboomMCU.PURPLE, 'Morado'),
    (YahboomMCU.CYAN,   'Cian'),
    (YahboomMCU.WHITE,  'Blanco'),
]

print('=== Test LED light bar (14 LEDs) ===\n')

try:
    print('--- Colores predefinidos (todos) ---')
    for color, name in COLORS:
        print(f'  {name}')
        mcu.led_all(1, color)
        time.sleep(0.8)
    mcu.led_off()
    time.sleep(0.5)

    print('\n--- Brillo RGB (todos) ---')
    steps = [(255,0,0,'Rojo'),(0,255,0,'Verde'),(0,0,255,'Azul'),(128,128,128,'Gris')]
    for r, g, b, name in steps:
        print(f'  RGB({r},{g},{b}) = {name}')
        mcu.led_rgb_all(r, g, b)
        time.sleep(0.8)
    mcu.led_rgb_all(0, 0, 0)
    time.sleep(0.5)

    print('\n--- LEDs individuales (1-14) ---')
    for i in range(1, 15):
        color = (i - 1) % 7
        mcu.led_one(i, 1, color)
        time.sleep(0.1)
    time.sleep(1.5)
    mcu.led_off()

    print('\n--- Efecto breathing rojo ---')
    for _ in range(3):
        for v in range(0, 256, 5):
            mcu.led_rgb_all(v, 0, 0)
            time.sleep(0.02)
        for v in range(255, -1, -5):
            mcu.led_rgb_all(v, 0, 0)
            time.sleep(0.02)
    mcu.led_rgb_all(0, 0, 0)

finally:
    mcu.led_off()
    mcu.close()
    print('\nFin')
