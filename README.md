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

> **RPi 5 nota:** el chip RP1 renumera todos los periféricos respecto a RPi 4.

| Periférico | Device en RPi 5      | Librería / herramienta          |
|------------|----------------------|---------------------------------|
| GPIO       | `/dev/gpiochip0`     | `libgpiod` / `python3-libgpiod` |
| I2C        | `/dev/i2c-13`, `/dev/i2c-14` | `smbus2` / `i2c-tools`  |
| SPI        | `/dev/spidev10.0`    | `spidev` (Python)               |
| UART       | `/dev/ttyAMA10`, `/dev/serial0` | `pyserial`           |
| Cámara     | `/dev/video0`        | `v4l2` / `ros2 v4l2_camera`     |

### Test rápido de GPIO (dentro del container)

```bash
# Listar chips GPIO
gpiodetect

# Listar pines del chip principal (40-pin header en RPi 5)
gpioinfo gpiochip4
```

### Test rápido de I2C

```bash
# Escanear dispositivos en bus 1
i2cdetect -y 1
```

## Notas

- El contenedor usa `network_mode: host` para que DDS (FastRTPS) descubra otros nodos en la red local sin configuración extra.
- Los artefactos de build (`build/`, `install/`, `log/`) se persisten en Docker volumes para no recompilar todo cada vez.
- El código fuente en `src/` se monta como bind mount — los cambios se reflejan inmediatamente dentro del contenedor.