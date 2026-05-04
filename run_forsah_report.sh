#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Run the Forsah tenders scraper and report generator.
.venv/bin/python forsah_tenders.py >> "$(pwd)/forsah_tenders_cron.log" 2>&1
