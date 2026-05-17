"""Launch the Streamlit dashboard.

Usage:
    streamlit run scripts/run_dashboard.py
"""
import sys
from pathlib import Path

# Ensure the project root is on the path so src imports resolve correctly.
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.dashboard.app import main

main()
