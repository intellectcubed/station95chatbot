#!/usr/bin/env python3
"""Generate curl commands to test the GroupMe webhook with realistic data."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("Note: python-dotenv not installed. Install with: pip install python-dotenv")
    print("      Or set environment variables manually\n")


def load_roster(roster_path: str = "data/roster.json") -> dict:
    """Load the roster file."""
    try:
        with open(roster_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Roster file not found at {roster_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in roster file: {e}")
        sys.exit(1)


def select_member(roster: dict) -> tuple[str, dict]:
    """Let user select a member from the roster."""
    members = roster.get('members', [])

    if not members:
        print("Error: No members found in roster")
        sys.exit(1)

    print("\n=== Select Sender ===")
    for i, member in enumerate(members, 1):
        squad = member.get('squad', 'Unknown')
        role = member.get('role', 'Member')
        print(f"{i}. {member['name']} (Squad {squad}, {role})")

    while True:
        try:
            choice = input(f"\nSelect member (1-{len(members)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(members):
                member = members[idx]
                return member['name'], member
            else:
                print(f"Please enter a number between 1 and {len(members)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)


def get_timestamp() -> int:
    """Get timestamp from user or use current time."""
    print("\n=== Message Timestamp ===")
    print("1. Use current UTC time")
    print("2. Enter custom date/time (UTC)")
    print("3. Enter relative time (e.g., -2h for 2 hours ago, relative to UTC)")

    while True:
        choice = input("\nSelect option (1-3): ").strip()

        if choice == "1":
            return int(datetime.now(timezone.utc).timestamp())

        elif choice == "2":
            print("\nEnter date and time (UTC):")
            date_str = input("  Date (YYYY-MM-DD) [today UTC]: ").strip()
            time_str = input("  Time (HH:MM) [now UTC]: ").strip()

            try:
                now = datetime.now(timezone.utc)

                # Parse date
                if date_str:
                    date_parts = date_str.split('-')
                    year = int(date_parts[0])
                    month = int(date_parts[1])
                    day = int(date_parts[2])
                else:
                    year, month, day = now.year, now.month, now.day

                # Parse time
                if time_str:
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                else:
                    hour, minute = now.hour, now.minute

                dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
                return int(dt.timestamp())

            except (ValueError, IndexError) as e:
                print(f"Invalid date/time format: {e}")
                continue

        elif choice == "3":
            relative_str = input("  Relative time (e.g., -2h, -30m, +1d): ").strip()

            try:
                import re
                match = re.match(r'([+-]?)(\d+)([hdm])', relative_str)
                if not match:
                    print("Invalid format. Use: +/-<number><h/d/m>")
                    continue

                sign = -1 if match.group(1) == '-' else 1
                amount = int(match.group(2))
                unit = match.group(3)

                now = datetime.now(timezone.utc)

                if unit == 'h':
                    from datetime import timedelta
                    dt = now + timedelta(hours=sign * amount)
                elif unit == 'm':
                    from datetime import timedelta
                    dt = now + timedelta(minutes=sign * amount)
                elif unit == 'd':
                    from datetime import timedelta
                    dt = now + timedelta(days=sign * amount)

                return int(dt.timestamp())

            except Exception as e:
                print(f"Error parsing relative time: {e}")
                continue

        else:
            print("Please select 1, 2, or 3")


def get_message_text() -> str:
    """Get message text from user."""
    print("\n=== Message Text ===")
    print("Examples:")
    print("  - Squad 34 no crew tonight")
    print("  - Squad 42 fully staffed this Saturday 0600-1800")
    print("  - No crew tomorrow evening")

    while True:
        text = input("\nEnter message text: ").strip()
        if text:
            return text
        print("Message cannot be empty")


def get_webhook_config() -> dict:
    """Get webhook URL and secret from environment or user input."""
    print("\n=== Webhook Configuration ===")

    # Try to load from environment (.env file or shell)
    import os

    # Webhook URL and secret (must be in .env or will prompt)
    default_url = os.environ.get('WEBHOOK_URL')
    default_secret = os.environ.get('WEBHOOK_SECRET')

    # GroupMe group ID (from .env file)
    default_group_id = os.environ.get('GROUPME_GROUP_ID')

    # Prompt for webhook URL
    if default_url:
        url = input(f"Webhook URL [{default_url}]: ").strip() or default_url
    else:
        url = input("Webhook URL (required): ").strip()
        if not url:
            print("Error: WEBHOOK_URL not set in .env and no input provided")
            sys.exit(1)

    # Prompt for webhook secret
    if default_secret:
        secret_display = f"{default_secret[:8]}..." if len(default_secret) > 8 else "***"
        secret = input(f"Webhook secret [{secret_display}]: ").strip() or default_secret
    else:
        secret = input("Webhook secret (required): ").strip()
        if not secret:
            print("Error: WEBHOOK_SECRET not set in .env and no input provided")
            sys.exit(1)

    # Prompt for group ID
    if default_group_id:
        group_id = input(f"Group ID [{default_group_id}]: ").strip() or default_group_id
    else:
        group_id = input("Group ID [test-group]: ").strip() or "test-group"

    return {
        'url': url,
        'secret': secret,
        'group_id': group_id
    }


def generate_curl_command(
    webhook_config: dict,
    sender_name: str,
    sender_member: dict,
    message_text: str,
    timestamp: int
) -> str:
    """Generate the curl command."""
    import random

    # Create the webhook payload
    payload = {
        "id": f"test-{random.randint(100000, 999999)}",
        "name": sender_name,
        "text": message_text,
        "sender_type": "user",
        "sender_id": str(random.randint(10000000, 99999999)),
        "created_at": timestamp,
        "group_id": webhook_config['group_id'],
        "system": False,
        "avatar_url": f"https://i.groupme.com/{random.randint(100, 999)}x{random.randint(100, 999)}.jpeg",
        "source_guid": f"test-guid-{random.randint(1000, 9999)}"
    }

    # Format the curl command
    payload_json = json.dumps(payload, indent=2)

    curl_command = f"""curl -X POST '{webhook_config['url']}?secret={webhook_config['secret']}' \\
  -H "Content-Type: application/json" \\
  -d '{payload_json}'"""

    return curl_command, payload


def main():
    """Main function."""
    print("=" * 60)
    print("  GroupMe Webhook Test Message Generator")
    print("=" * 60)

    # Load roster
    roster = load_roster()

    # Select member
    sender_name, sender_member = select_member(roster)

    # Get timestamp
    timestamp = get_timestamp()
    timestamp_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\nTimestamp: {timestamp_str} ({timestamp})")

    # Get message text
    message_text = get_message_text()

    # Get webhook config
    webhook_config = get_webhook_config()

    # Generate curl command
    curl_command, payload = generate_curl_command(
        webhook_config,
        sender_name,
        sender_member,
        message_text,
        timestamp
    )

    # Display results
    print("\n" + "=" * 60)
    print("  Generated Test Message")
    print("=" * 60)
    print(f"\nSender: {sender_name}")
    print(f"Squad: {sender_member.get('squad', 'Unknown')}")
    print(f"Role: {sender_member.get('role', 'Unknown')}")
    print(f"Timestamp: {timestamp_str}")
    print(f"Message: {message_text}")

    print("\n" + "=" * 60)
    print("  Webhook Payload")
    print("=" * 60)
    print(json.dumps(payload, indent=2))

    print("\n" + "=" * 60)
    print("  cURL Command")
    print("=" * 60)
    print(curl_command)

    # Option to copy to clipboard
    print("\n" + "=" * 60)

    save_choice = input("\nSave to file? (y/N): ").strip().lower()
    if save_choice == 'y':
        filename = f"test_webhook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
        with open(filename, 'w') as f:
            f.write("#!/bin/bash\n\n")
            f.write("# Generated test webhook command\n")
            f.write(f"# Sender: {sender_name}\n")
            f.write(f"# Timestamp: {timestamp_str}\n")
            f.write(f"# Message: {message_text}\n\n")
            f.write(curl_command)
            f.write("\n")

        import os
        os.chmod(filename, 0o755)
        print(f"✓ Saved to {filename}")
        print(f"  Run with: ./{filename}")

    print("\n✓ Done!")


"""
USAGE:

1. Set these variables in your .env file:
   WEBHOOK_URL=https://your-api-gateway-url.../webhook
   WEBHOOK_SECRET=your-secret-here
   GROUPME_GROUP_ID=your-group-id

2. Run the script (it will load .env automatically):
   python generate_test_curl.py

3. Follow the interactive prompts to:
   - Select a sender from the roster
   - Choose a timestamp (current, custom, or relative)
   - Enter the message text
   - Generate the curl command

If .env variables are not set, you will be prompted to enter them.
"""

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
