###############################################################################
# autobot-autonomy — ROS 2 Jazzy on Raspberry Pi 5
# Multi-stage build: dev image with full tooling
###############################################################################
ARG ROS_DISTRO=jazzy

# ============================================================================
# Base stage — ROS 2 Jazzy + hardware dependencies for Raspberry Pi 5
# ============================================================================
FROM ros:${ROS_DISTRO} AS base

ENV DEBIAN_FRONTEND=noninteractive

# ---- System & hardware libraries -------------------------------------------
# GPIO  : libgpiod (userspace GPIO — replaces deprecated sysfs & RPi.GPIO)
# I2C   : i2c-tools, libi2c-dev
# SPI   : spidev access (kernel module, no extra lib needed)
# Serial: libserial-dev
# Camera: libcamera, v4l-utils
# General: build tools, Python bindings
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    cmake \
    python3-pip \
    python3-colcon-common-extensions \
    # GPIO (gpiod — the modern way on RPi 5)
    gpiod \
    libgpiod-dev \
    python3-libgpiod \
    # I2C
    i2c-tools \
    libi2c-dev \
    # Serial / UART
    libserial-dev \
    # Camera & video
    v4l-utils \
    libcamera-dev \
    libcamera-tools \
    # Networking & debug
    iputils-ping \
    net-tools \
    nano \
    vim \
    gdb \
    # ROS 2 extras
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-v4l2-camera \
    ros-${ROS_DISTRO}-image-transport \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-diagnostic-updater \
    ros-${ROS_DISTRO}-joy \
    ros-${ROS_DISTRO}-web-video-server \
    && rm -rf /var/lib/apt/lists/*

# ---- Python packages (for driver development) -----------------------------
RUN pip3 install --no-cache-dir --break-system-packages \
    smbus2 \
    spidev \
    pyserial

# PyTorch CPU-only for aarch64 (skip ~2 GB of useless CUDA/NVIDIA deps)
# Pin numpy<2 — ROS 2 cv_bridge is compiled against numpy 1.x
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed "numpy<2" \
    && pip3 install --no-cache-dir --break-system-packages \
       --extra-index-url https://download.pytorch.org/whl/cpu \
       torch torchvision \
    && pip3 install --no-cache-dir --break-system-packages --no-deps \
       ultralytics \
    && pip3 install --no-cache-dir --break-system-packages \
       ultralytics-thop matplotlib pillow pyyaml requests tqdm psutil py-cpuinfo pandas seaborn

# ---- Auto-source ROS 2 + workspace for every interactive bash session ------
# Applies to `docker exec -it autobot bash` without needing to source manually.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /etc/bash.bashrc \
 && echo '[[ -f /ros2_ws/install/setup.bash ]] && source /ros2_ws/install/setup.bash' >> /etc/bash.bashrc

# ============================================================================
# Dev stage — workspace and entrypoint
# ============================================================================
FROM base AS dev

# Create the ROS 2 workspace
RUN mkdir -p /ros2_ws/src

WORKDIR /ros2_ws

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
