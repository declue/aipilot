"""
Configuration settings for the webhook server.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Base directory for the application
BASE_DIR = Path(__file__).parent.parent.absolute()

# Data directory for storing webhook payloads
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database settings
DATABASE_URL = "sqlite:///./webhook_clients.db"

# GitHub webhook secret
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# Server settings
HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Logging settings
LOG_FILE = BASE_DIR / "logs" / "webhook_server.log"
LOG_FILE.parent.mkdir(exist_ok=True)
LOG_ROTATION = "10 MB"
LOG_RETENTION = "7 days"

# API settings
API_PREFIX = "/api/v1"
API_TITLE = "GitHub Webhook Server"
API_VERSION = "1.0.0"
API_DESCRIPTION = "A server for receiving and relaying GitHub webhooks"

# Security settings
ENABLE_CORS = os.getenv("ENABLE_CORS", "false").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Rate limiting settings
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # requests per minute

def get_settings() -> Dict[str, Any]:
    """
    Returns all settings as a dictionary.
    """
    return {
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "database_url": DATABASE_URL,
        "github_webhook_secret": bool(GITHUB_WEBHOOK_SECRET),  # Just return if it's set, not the actual value
        "host": HOST,
        "port": PORT,
        "log_level": LOG_LEVEL,
        "log_file": str(LOG_FILE),
        "log_rotation": LOG_ROTATION,
        "log_retention": LOG_RETENTION,
        "api_prefix": API_PREFIX,
        "api_title": API_TITLE,
        "api_version": API_VERSION,
        "enable_cors": ENABLE_CORS,
        "cors_origins": CORS_ORIGINS,
        "rate_limit_enabled": RATE_LIMIT_ENABLED,
        "rate_limit": RATE_LIMIT,
    }