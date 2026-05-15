#!/usr/bin/env bash
set -euo pipefail

RULE_FILE="/etc/udev/rules.d/99-manus-wuji.rules"

if [ "${EUID}" -ne 0 ]; then
  exec sudo -E bash "$0" "$@"
fi

cat > "${RULE_FILE}" <<'EOF'
# MANUS Metagloves Pro dongle / HID access
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3325", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb", ATTR{idVendor}=="3325", MODE="0666", TAG+="uaccess"

# Wuji Hand USB device, commonly 0483:2000
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="2000", MODE="0666", TAG+="uaccess"
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="2000", MODE="0666", TAG+="uaccess"
EOF

udevadm control --reload-rules
udevadm trigger

echo "[ok] installed ${RULE_FILE}"
echo "[info] Replug the MANUS dongle and Wuji hand USB cable if they were already connected."
