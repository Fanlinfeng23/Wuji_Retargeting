#!/usr/bin/env bash
# Source this file in an interactive shell before manual ros2 topic/service checks:
#   source scripts/source_env.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"

source "${ROOT_DIR}/scripts/common.bash"
source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${ROOT_DIR}/wuji_ros2_ws/install/setup.bash"
source_ros_setup "${ROOT_DIR}/official_teleop_ws/install/setup.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export PYTHONPATH="${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROOT_DIR}/log/ros}"
mkdir -p "${ROS_LOG_DIR}"

echo "[ok] sourced MANUS -> Wuji teleop environment"
echo "[info] ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
