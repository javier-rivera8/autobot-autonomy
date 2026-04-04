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
    && rm -rf /var/lib/apt/lists/*

# ---- Python packages (for driver development) -----------------------------
RUN pip3 install --no-cache-dir --break-system-packages \
    smbus2 \
    spidev \
    pyserial

# ---- Auto-source ROS 2 for every interactive bash session ------------------
# This ensures ros2 commands work whether you exec into the container or
# the entrypoint starts it.
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /etc/bash.bashrc

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
