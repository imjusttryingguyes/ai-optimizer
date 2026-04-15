#!/usr/bin/env python3
"""
Phase 4 Analytics Dashboard - HuggingFace entry point
"""
import os
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

# Import and run the dashboard
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    exec(open('dashboard.py').read())
except ImportError as e:
    import streamlit as st
    st.error(f"Error loading dashboard: {e}")
