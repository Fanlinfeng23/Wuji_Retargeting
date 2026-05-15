#!/usr/bin/env bash
set -euo pipefail

patterns=(
  "ros2 launch .*/launch/manus_wuji_right.launch.py"
  "manus_data_publisher"
  "manus_input"
  "wujihand_controller"
  "wujihand_driver_node"
)

for pattern in "${patterns[@]}"; do
  pkill -f "${pattern}" 2>/dev/null || true
done

echo "[ok] stop signal sent to official MANUS -> Wuji teleop processes"
