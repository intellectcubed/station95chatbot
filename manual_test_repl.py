#!/usr/bin/env python3
"""
Interactive REPL for manually testing GroupMe webhook messages.

Run this script and enter messages interactively to test the bot.
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8081"


def send_webhook(sender_name, message_text, preview=False):
    """Send a webhook to the bot."""
    payload = {
        "attachments": [],
        "avatar_url": "https://i.groupme.com/123456789",
        "created_at": int(time.time()),
        "group_id": "12345678",
        "id": f"{int(time.time() * 1000)}",
        "name": sender_name,
        "sender_id": str(hash(sender_name) % 100000),
        "sender_type": "user",
        "system": False,
        "text": message_text,
        "user_id": str(hash(sender_name) % 100000),
        "preview": preview
    }

    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=payload,
            timeout=10
        )

        print(f"\n{'='*80}")
        print(f"✓ Status: {response.status_code}")
        try:
            result = response.json()
            print(f"✓ Response: {result}")
        except:
            print(f"✓ Response: {response.text}")
        print(f"{'='*80}\n")

    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Could not connect to {BASE_URL}")
        print("✗ Make sure the bot is running: python3 run.py")
        print()
    except requests.exceptions.RequestException as e:
        print(f"\n✗ ERROR: {e}\n")


def main():
    """Run the interactive REPL."""
    print("="*80)
    print("GroupMe Bot - Manual Test REPL")
    print("="*80)
    print(f"Target: {BASE_URL}/webhook")
    print()
    print("Commands:")
    print("  - Type 'quit' or 'exit' to stop")
    print("  - Press Ctrl+C to stop")
    print("  - Leave sender blank to use last sender")
    print("="*80)
    print()

    # Check if bot is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"✓ Bot is running (status: {response.json().get('status', 'unknown')})\n")
    except:
        print(f"⚠ WARNING: Bot may not be running at {BASE_URL}")
        print("  Start it with: python3 run.py\n")

    last_sender = "George Nowakowski"

    try:
        while True:
            # Get sender
            sender = input("Who is sending? [" + last_sender + "]: ").strip()
            if sender.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break

            if not sender:
                sender = last_sender
            else:
                last_sender = sender

            # Get message
            message = input("Message: ").strip()
            if message.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break

            if not message:
                print("⚠ Message cannot be empty. Try again.\n")
                continue

            # Get preview mode
            preview_input = input("Preview mode? [y/N]: ").strip().lower()
            preview = preview_input in ['y', 'yes', 'true', '1']

            # Send webhook
            print(f"\n→ Sending webhook...")
            print(f"  Sender: {sender}")
            print(f"  Message: {message}")
            print(f"  Preview: {preview}")

            send_webhook(sender, message, preview)

    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
