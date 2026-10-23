#!/usr/bin/env bash
echo "============================================================"
echo " Starting MNP Payroll Subsystem (BTM 495 Working Prototype)"
echo "============================================================"
echo ""

if command -v python3 &>/dev/null; then
    python3 app.py
elif command -v python &>/dev/null; then
    python app.py
else
    echo "[ERROR] Python not found on PATH."
    exit 1
fi
