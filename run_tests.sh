#!/usr/bin/env bash
echo "============================================================"
echo " Running MNP Payroll Subsystem Automated Verification"
echo "============================================================"
echo ""

if command -v python3 &>/dev/null; then
    python3 test_prototype.py
elif command -v python &>/dev/null; then
    python test_prototype.py
else
    echo "[ERROR] Python not found on PATH."
    exit 1
fi
