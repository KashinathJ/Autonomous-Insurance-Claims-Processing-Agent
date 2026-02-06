"""
Entry point to run the Streamlit app from project root.
Usage: python run_app.py   (or: streamlit run src/app.py)
Ensures dynamic paths and venv-friendly execution.
"""

import os
import sys
from pathlib import Path

# Project root = directory containing this script
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Run Streamlit programmatically so it uses PROJECT_ROOT as cwd
from streamlit.web import cli as st_cli

if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        str(PROJECT_ROOT / "src" / "app.py"),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    sys.exit(st_cli.main())
