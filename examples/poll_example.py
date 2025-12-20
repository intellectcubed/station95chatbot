#!/usr/bin/env python3
"""
Example script showing how to use the GroupMe poller programmatically.

This demonstrates how you can integrate the poller into your own scripts
or applications rather than using the CLI wrapper.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from station95chatbot.ai_processor import AIProcessor
from station95chatbot.calendar_client import CalendarClient
from station95chatbot.config import settings
from station95chatbot.groupme_poller import GroupMePoller
from station95chatbot.logging_config import setup_logging
from station95chatbot.message_processor import MessageProcessor
from station95chatbot.roster import Roster


def main():
    """Example of using the poller programmatically."""
    # Setup logging
    setup_logging()

    # Initialize all components
    roster = Roster(settings.roster_file_path)
    ai_processor = AIProcessor()
    calendar_client = CalendarClient()
    message_processor = MessageProcessor(roster, ai_processor, calendar_client)

    # Create poller with custom state file location
    poller = GroupMePoller(
        message_processor,
        state_file="data/my_custom_state.txt"  # Optional: use custom state file
    )

    # Example 1: Simple poll
    print("=" * 60)
    print("Running simple poll...")
    result = poller.poll(limit=20)

    print(f"\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Messages fetched: {result.get('messages_fetched', 0)}")
    print(f"  New messages: {result.get('messages_new', 0)}")
    print(f"  Processed: {result.get('messages_processed', 0)}")
    print(f"  Ignored: {result.get('messages_ignored', 0)}")

    # Example 2: Process individual results
    if result.get('results'):
        print("\nIndividual message results:")
        for item in result['results']:
            msg_id = item['message_id']
            msg_result = item['result']
            status = "✓ PROCESSED" if msg_result.get('processed') else "○ IGNORED"
            reason = msg_result.get('reason', 'N/A')
            print(f"  {status} | {msg_id[:10]}... | {reason}")

    # Example 3: Reset state (commented out - use carefully!)
    # print("\nResetting poller state...")
    # poller.reset_state()
    # print("State reset - next poll will reprocess messages")

    print("=" * 60)


if __name__ == "__main__":
    main()
