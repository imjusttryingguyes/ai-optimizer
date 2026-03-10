#!/bin/bash

cd /opt/ai-optimizer || exit 1
source venv/bin/activate
python analytics/segment_combinations_analysis.py