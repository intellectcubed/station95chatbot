"""Client for sending messages to GroupMe."""

import logging
import requests
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)


class GroupMeClient:
    """Client for sending messages to GroupMe group chat."""

    def __init__(self, bot_id: str | None = None):
        """Initialize the GroupMe client."""
        self.bot_id = bot_id or settings.groupme_bot_id
        self.api_url = "https://api.groupme.com/v3/bots/post"
        logger.info(f"Initialized GroupMeClient with bot_id: {self.bot_id}")

    def send_message(self, text: str) -> dict[str, Any]:
        """
        Send a message to the GroupMe group chat.

        Args:
            text: The message text to send

        Returns:
            Response from GroupMe API

        Raises:
            requests.RequestException: If the request fails
        """
        payload = {
            "bot_id": self.bot_id,
            "text": text,
        }

        logger.info(f"Sending message to GroupMe: {text[:100]}...")

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=10,
            )

            response.raise_for_status()

            logger.info(f"Message sent successfully: {response.status_code}")

            # GroupMe returns 202 Accepted for successful bot posts
            return {"status": "success", "response": response.text}

        except requests.RequestException as e:
            logger.error(f"Error sending message to GroupMe: {e}")
            raise

    def send_warning(self, warning_text: str) -> dict[str, Any]:
        """
        Send a warning message to the GroupMe group chat with formatting.

        Args:
            warning_text: The warning message to send

        Returns:
            Response from GroupMe API
        """
        formatted_message = f"⚠️ WARNING ⚠️\n{warning_text}"
        return self.send_message(formatted_message)

    def send_critical_alert(self, alert_text: str) -> dict[str, Any]:
        """
        Send a critical alert message to the GroupMe group chat with formatting.

        Args:
            alert_text: The critical alert message to send

        Returns:
            Response from GroupMe API
        """
        formatted_message = f"🚨 CRITICAL ALERT 🚨\n{alert_text}"
        return self.send_message(formatted_message)
