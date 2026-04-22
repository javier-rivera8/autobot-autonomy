# Autobot Autonomy

Stack de autonomía from-scratch para RaspBot Yahboom sobre **Raspberry Pi 5** con **ROS 2 Jazzy** en Docker.

No se usa ningún paquete de Yahboom — drivers de motores, cámara y sensores se implementan desde cero.

---

## Estructura del proyecto

```
autobot-autonomy/
├── docker/
│   └── Dockerfile          # Imagen ROS 2 Jazzy + deps hardware RPi 5
├── docker-compose.yml      # Orquestación del contenedor
├── entrypoint.sh           # Sourcea ROS 2 al entrar al container
├── src/                    # ROS 2 workspace (packages van aquí)
├── .dockerignore
└── README.md
```

## Requisitos previos (en la Raspberry Pi 5)

1. **Raspberry Pi OS** (64-bit, Bookworm recomendado).
2. **Docker** y **Docker Compose v2** instalados:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # reloguear o: newgrp docker
   ```
3. **Habilitar interfaces de hardware** (si no lo están):
   ```bash
   sudo raspi-config
   # → Interface Options → enable: I2C, SPI, Serial Port, Camera
   ```
4. Verificar que los devices existen:
   ```bash
   ls /dev/gpiochip* /dev/i2c-* /dev/spidev* /dev/video* /dev/ttyAMA0
   ```

## Uso rápido

```bash
# Clonar el repo
git clone <repo-url> autobot-autonomy && cd autobot-autonomy

# Construir la imagen
docker compose build

# Levantar el contenedor
docker compose up -d

# Entrar al contenedor
docker compose exec autobot bash

# Dentro del contenedor — verificar ROS 2
ros2 doctor --report

# Compilar el workspace (cuando tengas paquetes en src/)
colcon build --symlink-install
source install/setup.bash
```

## Acceso al hardware desde el contenedor

> **RPi 5 nota:** el chip RP1 renumera los buses internos, pero el I2C del header (GPIO2/GPIO3) sigue siendo `/dev/i2c-1`.

| Periférico | Device en RPi 5      | Librería / herramienta          |
|------------|----------------------|---------------------------------|
| GPIO       | `/dev/gpiochip0`     | `libgpiod` / `python3-libgpiod` |
| I2C (header)| `/dev/i2c-1` → MCU `0x2b` | `smbus2` / `i2c-tools`   |
| SPI        | `/dev/spidev10.0`    | `spidev` (Python)               |
| UART       | `/dev/ttyAMA10`, `/dev/serial0` | `pyserial`           |
| Cámara     | `/dev/video0`        | `v4l2` / `ros2 v4l2_camera`     |

### MCU coprocessor — protocolo I2C

Address: `0x2b` en `/dev/i2c-1`

| Registro | Operación | Datos |
|----------|-----------|-------|
| `0x01` | Mover un motor | `[motor_id, dir, speed]` — dir: `1`=adelante `0`=atrás, speed: `0-100` |
| `0x02` | Stop | write_byte `0x00` |
| `0x03` | Servo | `[id, angle]` — angle: `0-180` |
| `0x06` | Buzzer | TBD |
| `0x08` | RGB LEDs | TBD |

Motor IDs (verificados por hardware probing):

| Motor ID | Posición física |
|----------|-----------------|
| `0` | Front-Left (M4) |
| `1` | Rear-Left  (M1) |
| `2` | Front-Right (M2) |
| `3` | Rear-Right  (M3) |

### Test rápido de GPIO (dentro del container)

```bash
# Listar chips GPIO
gpiodetect

# Listar pines del chip principal (40-pin header en RPi 5, 54 lines)
gpioinfo gpiochip0
```

### Test rápido de I2C

```bash
# Escanear el bus del header (GPIO2/GPIO3)
sudo i2cdetect -y -r 1
# Esperado: 0x2b → MCU coprocessor

# Verificar motores (robot levantado)
# [motor_id, dir=adelante, speed=60]
sudo i2cset -y 1 0x2b 0x01 0 1 60 i  # FL
sudo i2cset -y 1 0x2b 0x01 2 1 60 i  # FR
sudo i2cset -y 1 0x2b 0x01 1 1 60 i  # RL
sudo i2cset -y 1 0x2b 0x01 3 1 60 i  # RR
```

## Notas

- El contenedor usa `network_mode: host` para que DDS (FastRTPS) descubra otros nodos en la red local sin configuración extra.
- Los artefactos de build (`build/`, `install/`, `log/`) se persisten en Docker volumes para no recompilar todo cada vez.
- El código fuente en `src/` se monta como bind mount — los cambios se reflejan inmediatamente dentro del contenedor.

## WEBSERVER
http://192.168.0.52:8080/stream?topic=/image_raw

http://192.168.0.52:8080/stream?topic=/image_annotated

## CAMBIOS EN EL DOCKER
docker compose up --build -d