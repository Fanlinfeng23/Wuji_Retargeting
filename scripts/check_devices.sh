#!/usr/bin/env bash
set -euo pipefail

echo "[check] USB devices"
if command -v lsusb >/dev/null 2>&1; then
  if lsusb -d 3325: >/dev/null 2>&1; then
    lsusb -d 3325:
  else
    echo "[warn] MANUS dongle not found with vendor id 3325"
  fi

  if lsusb -d 0483:2000 >/dev/null 2>&1; then
    lsusb -d 0483:2000
  else
    echo "[warn] Wuji hand not found as 0483:2000"
    echo "       If your firmware exposes a different product id, check plain lsusb output."
  fi
else
  echo "[warn] lsusb not found; install usbutils"
fi

echo
echo "[check] Device nodes"
ls -l /dev/hidraw* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
