#!/usr/bin/env bash
set -euo pipefail

# Ensure the script runs from the project directory so .env is loaded correctly.
cd "$(dirname "$0")"

# Use the virtualenv Python interpreter directly.
# Schedule this script at 09:00, 11:00, 13:00, and 15:00 Saudi time via cron.
.venv/bin/python tenders_report_etimad.py >> "$(pwd)/bt_tndrs_etimad_cron.log" 2>&1
