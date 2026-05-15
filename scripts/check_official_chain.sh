#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO="${ROS_DISTRO:-humble}"
source "${ROOT_DIR}/scripts/common.bash"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${ROOT_DIR}/log/ros}"
export PYTHONPATH="${ROOT_DIR}/third_party/wuji_official:${PYTHONPATH:-}"
mkdir -p "${ROS_LOG_DIR}"

source_ros_setup "/opt/ros/${ROS_DISTRO}/setup.bash"
source_ros_setup "${ROOT_DIR}/wuji_ros2_ws/install/setup.bash"
source_ros_setup "${ROOT_DIR}/official_teleop_ws/install/setup.bash"

echo "[check] official package visibility"
ros2 pkg prefix manus_input_py >/dev/null
ros2 pkg prefix controller >/dev/null
ros2 pkg prefix wujihand_output >/dev/null
ros2 pkg prefix wuji_teleop_bringup >/dev/null
ros2 pkg prefix wujihand_driver >/dev/null
ros2 pkg prefix manus_ros2 >/dev/null

echo "[check] official launch arguments"
ros2 launch wuji_teleop_bringup wuji_teleop_hand.launch.py --show-args >/dev/null

echo "[check] official retargeter import"
WUJI_RETARGETING_ROOT="${ROOT_DIR}" /usr/bin/python3 - <<'PY'
import os
import numpy as np
from pathlib import Path
from wuji_retargeting import Retargeter

root = Path(os.environ["WUJI_RETARGETING_ROOT"])
cfg = root / "wuji-hand-teleop/src/output_devices/wujihand_output/config/retarget_manus_right.yaml"
r = Retargeter.from_yaml(str(cfg), "right")

# Non-degenerate MediaPipe-like right-hand landmarks in meters.  The retargeter
# estimates a wrist frame from wrist/index/middle MCPs, so all-zero keypoints
# are not a valid smoke-test input.
kp = np.array([
    [0.00, 0.00, 0.00],
    [-0.02, 0.01, 0.00], [-0.035, 0.025, 0.005], [-0.045, 0.04, 0.01], [-0.055, 0.055, 0.015],
    [0.025, 0.015, 0.00], [0.03, 0.045, 0.005], [0.033, 0.075, 0.006], [0.035, 0.105, 0.006],
    [0.000, 0.020, 0.00], [0.000, 0.055, 0.005], [0.000, 0.090, 0.006], [0.000, 0.125, 0.006],
    [-0.022, 0.015, 0.00], [-0.028, 0.050, 0.004], [-0.032, 0.080, 0.005], [-0.035, 0.110, 0.005],
    [-0.045, 0.010, 0.00], [-0.055, 0.040, 0.003], [-0.062, 0.065, 0.004], [-0.068, 0.090, 0.004],
], dtype=np.float32)
q = r.retarget(kp)
assert q.shape == (20,)
assert np.isfinite(q).all()
print("[check] retargeter ok")
PY

echo "[check] official chain is buildable and discoverable"
