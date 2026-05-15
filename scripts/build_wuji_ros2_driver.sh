#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WUJI_WS="${ROOT_DIR}/wuji_ros2_ws"
ROS_DISTRO="${ROS_DISTRO:-humble}"
source "${ROOT_DIR}/scripts/common.bash"

if [ "${WUJI_CLEAN_ENV:-0}" != "1" ]; then
  exec env -i \
    HOME="${HOME}" \
    USER="${USER:-user}" \
    LOGNAME="${LOGNAME:-${USER:-user}}" \
    SHELL=/bin/bash \
    TERM="${TERM:-xterm}" \
    LANG="${LANG:-C.UTF-8}" \
    LC_ALL="${LC_ALL:-C.UTF-8}" \
    PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    WUJI_CLEAN_ENV=1 \
    bash --noprofile --norc "$0" "$@"
fi

mkdir -p "${WUJI_WS}/src"
if [ ! -e "${WUJI_WS}/src/wujihandros2" ]; then
  ln -s "${ROOT_DIR}/third_party/wujihandros2" "${WUJI_WS}/src/wujihandros2"
fi

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
export PYTHON_EXECUTABLE="${PYTHON_EXECUTABLE:-/usr/bin/python3}"
export Python3_EXECUTABLE="${Python3_EXECUTABLE:-/usr/bin/python3}"
cd "${WUJI_WS}"
exec colcon build --symlink-install --cmake-args -DPython3_EXECUTABLE="${Python3_EXECUTABLE}"
