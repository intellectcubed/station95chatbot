#!/usr/bin/env python3
"""Test script for agentic AI workflow with mock webhooks."""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

# Complex test messages for agentic mode
TEST_MESSAGES = [
    {
        "sender": "George Nowakowski",
        "text": "42 will not have a crew tonight midnight - 6 or Thursday midnight - 6",
        "description": "Multiple noCrew commands"
    },
    {
        "sender": "Katie Sowden",
        "text": "35 out tonight and tomorrow morning",
        "description": "Two different shifts"
    },
    {
        "sender": "Mike B",
        "text": "Remove Squad 42 from tonight's evening shift",
        "description": "Should check if station goes out of service"
    },
    {
        "sender": "George Nowakowski",
        "text": "43 does not have a crew tonight. Add 43 for Saturday morning instead",
        "description": "Remove one, add another"
    }
]


def create_webhook_payload(sender_name, text):
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
        "user_id": str(hash(sender_name) % 100000)
    }


def test_webhook(sender, text, description):
    """Send a test webhook to the bot."""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {description}")
    print(f"👤 Sender: {sender}")
    print(f"💬 Message: {text}")
    print(f"{'='*80}")

    payload = create_webhook_payload(sender, text)

    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=payload,
            timeout=60  # Agentic mode can take longer
        )

        print(f"\n✅ Status Code: {response.status_code}")

        result = response.json()
        print(f"\n📊 RESULTS:")
        print(f"  Processed: {result.get('processed', False)}")
        print(f"  Commands sent: {result.get('command_sent', False)}")

        if 'interpretation' in result:
            interp = result['interpretation']
            print(f"  Is shift request: {interp.get('is_shift_request', False)}")
            print(f"  Confidence: {interp.get('confidence', 0)}%")

            if 'parsed_requests' in interp:
                print(f"  Parsed requests: {len(interp['parsed_requests'])}")
                for i, req in enumerate(interp['parsed_requests'], 1):
                    print(f"    {i}. {req.get('action')} - Squad {req.get('squad')} - {req.get('date')}")

            if interp.get('warnings'):
                print(f"\n  ⚠️  Warnings:")
                for w in interp['warnings']:
                    print(f"    - {w}")

            if interp.get('critical_warnings'):
                print(f"\n  🚨 Critical Warnings:")
                for w in interp['critical_warnings']:
                    print(f"    - {w}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🚀 AGENTIC AI WORKFLOW - LOCAL TESTING")
    print("="*80 + "\n")

    # Check if bot is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Bot is running (status: {response.json()['status']})")
        print(f"✓ Make sure AI_MODE=agentic is set\n")
    except requests.exceptions.RequestException:
        print("✗ Bot is not running! Start it with: python run.py")
        print("✗ Make sure AI_MODE=agentic in .env\n")
        return

    # Run tests
    for test in TEST_MESSAGES:
        test_webhook(test["sender"], test["text"], test["description"])
        print("\n⏳ Waiting 3 seconds before next test...\n")
        time.sleep(3)

    print("="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
    print("\n📝 Check logs for detailed workflow execution:")
    print(f"   - logs/chatbot.log")
    print(f"   - logs/message_log_{datetime.now().strftime('%Y%m%d')}.jsonl\n")


if __name__ == "__main__":
    main()
