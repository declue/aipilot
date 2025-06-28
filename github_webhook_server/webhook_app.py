"""
GitHub Webhook Server - Legacy Entry Point

This file is maintained for backward compatibility.
For new development, please use the modular structure in the webhook package.
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the new modular structure
from main import app, init_app, run_app

# Initialize the application
init_app()

# Run the application if this file is executed directly
if __name__ == "__main__":
    run_app()