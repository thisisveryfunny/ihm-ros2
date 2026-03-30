#!/bin/bash
set -e

# Source ROS2 Humble
source /opt/ros/humble/setup.bash

# Activate virtual env (pip packages)
source /opt/venv/bin/activate

exec "$@"
