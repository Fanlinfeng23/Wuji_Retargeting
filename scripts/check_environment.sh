#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WUJI_WS="${ROOT_DIR}/wuji_ros2_ws"
ROS_DISTRO="${ROS_DISTRO:-humble}"
source "${ROOT_DIR}/scripts/common.bash"

echo "[check] root: ${ROOT_DIR}"
test -f "/opt/ros/${ROS_DISTRO}/setup.bash"
test -f "${ROOT_DIR}/official_teleop_ws/install/setup.bash"
test -d "${ROOT_DIR}/third_party/wuji_official/wuji_retargeting"
test -d "${ROOT_DIR}/third_party/wujihandros2"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
if [ -f "${WUJI_WS}/install/setup.bash" ]; then
  source_ros_setup "${WUJI_WS}/install/setup.bash"
else
  echo "[warn] ${WUJI_WS}/install/setup.bash not found; run scripts/build_wuji_ros2_driver.sh"
fi
source_ros_setup "${ROOT_DIR}/official_teleop_ws/install/setup.bash"

/usr/bin/python3 - <<'PY'
import importlib.util
import sys

required = ["numpy", "scipy", "nlopt", "yaml", "rclpy", "sensor_msgs", "std_msgs", "manus_ros2_msgs"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print("[error] missing modules:", ", ".join(missing))
    sys.exit(1)
print("[check] python modules ok")
PY

MANUS_SDK_LIB="${ROOT_DIR}/wuji-hand-teleop/src/input_devices/manus_input/manus_ros2/ManusSDK/lib/libManusSDK_Integrated.so"
if is_real_elf_shared_object "${MANUS_SDK_LIB}"; then
  echo "[check] MANUS SDK library ok"
else
  echo "[error] MANUS SDK library is not a real ELF shared object: ${MANUS_SDK_LIB}" >&2
  echo "        run ./scripts/prepare_manus_sdk.sh or git lfs pull" >&2
  exit 1
fi

if command -v ros2 >/dev/null 2>&1; then
  echo "[check] ros2: $(command -v ros2)"
else
  echo "[error] ros2 not found"
  exit 1
fi

echo "[check] environment looks usable"
