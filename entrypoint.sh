#!/usr/bin/env bash
set -e

# Source ROS 2 base setup
source /opt/ros/${ROS_DISTRO}/setup.bash

# Build the workspace on every start so code changes take effect
echo '[entrypoint] Building workspace...'
cd /ros2_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5

# Source the freshly built workspace
source /ros2_ws/install/setup.bash

# Launch all nodes in the background (motor driver, camera, web video server)
echo '[entrypoint] Launching autobot nodes...'
ros2 launch autobot_drivers bringup.launch.py &
export AUTOBOT_LAUNCH_PID=$!

exec "$@"
