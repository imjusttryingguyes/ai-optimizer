#!/usr/bin/env python3
"""
Phase 4 Analytics Dashboard - HuggingFace entry point
"""
import os
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

# On HF Space: Try to pull latest code from GitHub
import subprocess
import sys
try:
    result = subprocess.run(
        ['git', 'pull', '--quiet'], 
        cwd=os.path.dirname(os.path.abspath(__file__)) + '/..', 
        capture_output=True, 
        timeout=5
    )
except Exception:
    pass  # Silently fail if git not available or not a git repo

# Import and run the dashboard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    exec(open('dashboard.py').read())
except ImportError as e:
    import streamlit as st
    st.error(f"Error loading dashboard: {e}")
