"""Client for interacting with the calendar service."""

import logging
import os
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

        logger.info(
            f"Sending command to calendar service: {command.action} "
            f"for squad {command.squad} on {command.date} "
            f"({command.shift_start}-{command.shift_end}) [preview={command.preview}]"
        )

        try:
            # Check if running in Lambda and need to sign requests with IAM
            if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                logger.debug("Using IAM authentication for calendar service")
                response = self._send_with_iam_auth(self.base_url, params)
            else:
                # Local development - no IAM signing
                logger.debug("Using plain HTTP request (no IAM auth)")
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

    def _send_with_iam_auth(self, url: str, params: dict) -> requests.Response:
        """
        Send a request with AWS IAM authentication (SigV4).

        Args:
            url: The URL to send the request to
            params: Query parameters

        Returns:
            Response object
        """
        from requests_aws4auth import AWS4Auth
        import boto3

        # Get AWS credentials from the Lambda execution environment
        session = boto3.Session()
        credentials = session.get_credentials()

        # Parse region from URL (e.g., us-east-1 from execute-api.us-east-1.amazonaws.com)
        import re
        region_match = re.search(r'\.([a-z]{2}-[a-z]+-\d)\.amazonaws\.com', url)
        region = region_match.group(1) if region_match else os.environ.get('AWS_REGION', 'us-east-1')

        # Create SigV4 auth
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'execute-api',
            session_token=credentials.token
        )

        # Send signed request
        return requests.get(url, params=params, auth=auth, timeout=10)

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
