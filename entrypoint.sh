#!/usr/bin/env bash
set -e

# Source ROS 2 base setup
source /opt/ros/${ROS_DISTRO}/setup.bash

# If the workspace has been built, source it too
if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

exec "$@"
