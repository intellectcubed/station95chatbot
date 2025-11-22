"""Client for interacting with the calendar service."""

import logging
import requests
from typing import Any

from .config import settings
from .models import CalendarCommand

logger = logging.getLogger(__name__)


class CalendarClient:
    """Client for sending commands to the calendar service."""

    def __init__(self, base_url: str | None = None):
        """Initialize the calendar client."""
        self.base_url = base_url or settings.calendar_service_url
        logger.info(f"Initialized CalendarClient with base URL: {self.base_url}")

    def send_command(self, command: CalendarCommand) -> dict[str, Any]:
        """
        Send a command to the calendar service.

        Args:
            command: The CalendarCommand to execute

        Returns:
            Response from the calendar service

        Raises:
            requests.RequestException: If the request fails
        """
        params = command.to_query_params()
        params["preview"] = "False"  # Add preview parameter

        logger.info(
            f"Sending command to calendar service: {command.action} "
            f"for squad {command.squad} on {command.date} "
            f"({command.shift_start}-{command.shift_end})"
        )

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10,
            )

            response.raise_for_status()

            logger.info(f"Command executed successfully: {response.status_code}")

            # Try to parse JSON response, fall back to text
            try:
                return response.json()
            except ValueError:
                return {"status": "success", "message": response.text}

        except requests.RequestException as e:
            logger.error(f"Error sending command to calendar service: {e}")
            raise

    def send_command_with_retry(
        self, command: CalendarCommand, max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Send a command with retry logic.

        Args:
            command: The CalendarCommand to execute
            max_retries: Maximum number of retry attempts

        Returns:
            Response from the calendar service
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return self.send_command(command)
            except requests.RequestException as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    logger.info("Retrying...")
                    continue
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise last_error

        raise last_error
