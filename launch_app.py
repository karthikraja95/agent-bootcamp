"""Launcher script for the AML Fraud Detection Gradio UI.

This script properly sets up the Python path and launches the Gradio app.

Why this launcher is needed:
- The app has a local package named 'agents' (src/fraud_detection/agents/)
- This conflicts with the 'agents' package from openai-agents when using `gradio` command
- This launcher ensures proper import resolution by setting up the Python path correctly

Usage:
    uv run --env-file .env python launch_app.py
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and launch the app
from src.fraud_detection.app import demo

if __name__ == "__main__":
    demo.launch(share=True)

