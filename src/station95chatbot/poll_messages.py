#!/usr/bin/env python3
"""CLI script to poll GroupMe for new messages.

This script can be run periodically by cron or other schedulers.

Example cron entry (every 2 minutes):
    */2 * * * * cd /path/to/project && python -m station95chatbot.poll_messages

Example systemd timer or AWS EventBridge schedule:
    rate(2 minutes)
"""

import logging
import sys
from pathlib import Path

from .ai_processor import AIProcessor
from .calendar_client import CalendarClient
from .config import settings
from .groupme_poller import GroupMePoller
from .logging_config import setup_logging
from .message_processor import MessageProcessor
from .roster import Roster

logger = logging.getLogger(__name__)


def validate_configuration() -> None:
    """Validate that all required configuration is present."""
    errors = []

    # Check GroupMe configuration
    if not settings.groupme_api_token:
        errors.append("GROUPME_API_TOKEN is not set")
    if not settings.groupme_group_id:
        errors.append("GROUPME_GROUP_ID is not set")

    # Check AI provider configuration
    try:
        settings.validate_ai_config()
    except ValueError as e:
        errors.append(str(e))

    # Check roster file exists
    if not Path(settings.roster_file_path).exists():
        errors.append(f"Roster file not found: {settings.roster_file_path}")

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError(
            "Configuration validation failed. Please check your .env file and "
            "ensure all required variables are set."
        )

    logger.info("Configuration validated successfully")


def main() -> None:
    """Main entry point for polling script."""
    # Setup logging
    setup_logging()
    logger.info("Starting GroupMe message poll")

    try:
        # Validate configuration
        validate_configuration()

        # Initialize components
        roster = Roster(settings.roster_file_path)
        logger.info(f"Loaded roster with {len(roster.members)} members")

        ai_processor = AIProcessor()
        logger.info(f"AI processor initialized with provider: {settings.ai_provider}")

        calendar_client = CalendarClient()
        logger.info(f"Calendar client initialized: {settings.calendar_service_url}")

        message_processor = MessageProcessor(roster, ai_processor, calendar_client)
        logger.info("Message processor initialized")

        # Initialize and run poller
        poller = GroupMePoller(message_processor)

        # Poll for up to 20 recent messages
        result = poller.poll(limit=20)

        # Log summary
        if result.get("success"):
            logger.info(
                f"Poll completed successfully: "
                f"{result.get('messages_new', 0)} new messages, "
                f"{result.get('messages_processed', 0)} processed, "
                f"{result.get('messages_ignored', 0)} ignored"
            )

            # Exit with success code
            sys.exit(0)
        else:
            logger.error(f"Poll failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error during poll: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
