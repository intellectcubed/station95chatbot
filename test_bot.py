#!/usr/bin/env python3
"""Test script to send mock GroupMe webhooks to the bot."""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8081"

# Sample test messages
TEST_MESSAGES = [
    {
        "sender": "George Nowakowski",
        "text": "43 does not have a crew tonight from 1800 to midnight",
        "description": "No crew tonight - partial shift"
    },
    {
        "sender": "Katie Sowden",
        "text": "35 does not have a crew for Saturday morning",
        "description": "No crew Saturday morning"
    },
    {
        "sender": "Mike B",
        "text": "54 is fully staffed tonight",
        "description": "Crew available"
    },
    {
        "sender": "George Nowakowski",
        "text": "Hey everyone, just checking in!",
        "description": "Non-shift message (should be ignored)"
    },
    {
        "sender": "Unknown Person",
        "text": "42 has no crew tonight",
        "description": "Unauthorized sender (should be ignored)"
    },
    {
        "sender": "Kholer",
        "text": "42 does not have a crew tonight from 1800 - midnight",
        "description": "No crew with specific time range"
    },
    {
        "sender": "Mike Halperin",
        "text": "Still no luck getting a crew until midnight. Fully staffed after midnight",
        "description": "Complex message - two shifts"
    },
    {
        "sender": "George Nowakowski",
        "text": "43 does not have a crew on March 15th from 1800 to midnight",
        "description": "Preview mode test (should send preview=True)",
        "preview": True  # Test preview mode
    }
]

def create_webhook_payload(sender_name, text, preview=False):
    """Create a mock GroupMe webhook payload."""
    return {
        "attachments": [],
        "avatar_url": "https://i.groupme.com/123456789",
        "created_at": int(time.time()),
        "group_id": "12345678",
        "id": f"{int(time.time() * 1000)}",
        "name": sender_name,
        "sender_id": str(hash(sender_name) % 100000),
        "sender_type": "user",
        "system": False,
        "text": text,
        "user_id": str(hash(sender_name) % 100000),
        "preview": preview  # Add preview flag
    }

def test_webhook(sender, text, description, preview=False):
    """Send a test webhook to the bot."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"Sender: {sender}")
    print(f"Message: {text}")
    print(f"Preview: {preview}")
    print(f"{'='*80}")

    payload = create_webhook_payload(sender, text, preview)

    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=payload,
            timeout=30
        )

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def main():
    """Run all tests."""
    print("Starting bot tests...")
    print(f"Target: {BASE_URL}")

    # Check if bot is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Bot is running (status: {response.json()['status']})\n")
    except requests.exceptions.RequestException:
        print("✗ Bot is not running! Start it with: python run.py")
        return

    # Run tests
    for test in TEST_MESSAGES:
        # Get preview flag from test, default to False
        preview = test.get("preview", False)
        test_webhook(test["sender"], test["text"], test["description"], preview)
        time.sleep(2)  # Wait between tests

    print(f"\n{'='*80}")
    print("All tests completed!")
    print(f"Check logs/chatbot.log for detailed processing logs")
    print(f"Check logs/message_log_{datetime.now().strftime('%Y%m%d')}.jsonl for message details")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
