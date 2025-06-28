"""
Test script for the GitHub Webhook Server.

This script sends a test webhook event to the server and verifies that it was received and processed correctly.
"""
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime

import requests

# Configuration
WEBHOOK_URL = "http://localhost:8000/api/v1/webhook"
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
TEST_EVENT_TYPE = "ping"
TEST_DELIVERY_ID = f"test-delivery-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def generate_signature(payload_body: bytes) -> str:
    """Generate a GitHub webhook signature."""
    if not WEBHOOK_SECRET:
        return ""

    hash_object = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    return "sha256=" + hash_object.hexdigest()


def send_test_webhook() -> None:
    """Send a test webhook event to the server."""
    # Create a test payload
    payload = {
        "zen": "Testing is good.",
        "hook_id": 12345,
        "hook": {
            "type": "Repository",
            "id": 12345,
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "content_type": "json",
                "insecure_ssl": "0",
                "url": WEBHOOK_URL,
            },
        },
        "repository": {
            "id": 54321,
            "name": "test-repo",
            "full_name": "test-org/test-repo",
            "owner": {
                "login": "test-org",
                "id": 98765,
                "type": "Organization",
            },
        },
        "sender": {
            "login": "test-user",
            "id": 12345,
            "type": "User",
        },
    }

    # Convert payload to JSON
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode("utf-8")

    # Generate signature
    signature = generate_signature(payload_bytes)

    # Set headers
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": TEST_EVENT_TYPE,
        "X-GitHub-Delivery": TEST_DELIVERY_ID,
        "User-Agent": "GitHub-Hookshot/test",
    }

    if signature:
        headers["X-Hub-Signature-256"] = signature

    # Send request
    print(f"Sending {TEST_EVENT_TYPE} webhook to {WEBHOOK_URL}...")
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=payload_bytes,
            headers=headers,
            timeout=10,
        )

        # Check response
        if response.status_code == 200:
            print(f"✅ Webhook sent successfully! (Status: {response.status_code})")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Webhook failed! (Status: {response.status_code})")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Is the server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_server_health() -> bool:
    """Check if the server is healthy."""
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is healthy! (Status: {response.status_code})")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Server health check failed! (Status: {response.status_code})")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Is the server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main() -> None:
    """Main function."""
    print("GitHub Webhook Server Test")
    print("=========================")

    # Check if server is running
    if not check_server_health():
        print("Please start the server first with: python main.py")
        sys.exit(1)

    # Send test webhook
    if send_test_webhook():
        print("\nTest completed successfully!")
    else:
        print("\nTest failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()