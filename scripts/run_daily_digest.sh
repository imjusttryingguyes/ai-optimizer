#!/usr/bin/env bash
set -euo pipefail

cd /opt/ai-optimizer
source venv/bin/activate
python telegram/daily_digest.py