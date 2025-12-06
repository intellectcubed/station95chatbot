"""Main entry point for the Station 95 GroupMe chatbot."""

import logging
import sys
from pathlib import Path

from .ai_processor import AIProcessor
from .calendar_client import CalendarClient
from .config import settings
from .logging_config import setup_logging
from .message_processor import MessageProcessor
from .roster import Roster
from .webhook_handler import WebhookHandler

logger = logging.getLogger(__name__)


def validate_configuration() -> None:
    """Validate that all required configuration is present."""
    errors = []

    # Check GroupMe configuration
    if not settings.groupme_bot_id:
        errors.append("GROUPME_BOT_ID is not set")
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
            "ensure all required variables are set. See .env.example for reference."
        )

    logger.info("Configuration validated successfully")


def main() -> None:
    """Main entry point for the application."""
    # Setup logging first
    setup_logging()
    logger.info("Starting Station 95 GroupMe Chatbot")

    try:
        # Validate configuration
        validate_configuration()

        # Initialize components
        logger.info("Initializing components...")

        roster = Roster(settings.roster_file_path)
        logger.info(f"Loaded roster with {len(roster.members)} members")

        ai_processor = AIProcessor()
        logger.info(f"AI processor initialized with provider: {settings.ai_provider}")

        calendar_client = CalendarClient()
        logger.info(f"Calendar client initialized: {settings.calendar_service_url}")

        message_processor = MessageProcessor(roster, ai_processor, calendar_client)
        logger.info("Message processor initialized")

        webhook_handler = WebhookHandler(message_processor)
        logger.info("Webhook handler initialized")

        # Start the webhook server
        logger.info(f"Starting webhook server on port {settings.webhook_port}")
        logger.info(
            "Bot is ready to receive messages. Configure your GroupMe bot webhook to "
            f"point to http://your-server:{settings.webhook_port}/webhook"
        )

        webhook_handler.run()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping bot...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
