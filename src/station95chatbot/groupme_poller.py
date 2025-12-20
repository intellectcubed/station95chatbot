"""GroupMe message poller for periodic message checking."""

import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings
from .models import GroupMeMessage
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class GroupMePoller:
    """Polls GroupMe for new messages and processes them."""

    def __init__(self, message_processor: MessageProcessor, state_file: str = "data/last_message_id.txt"):
        """
        Initialize the GroupMe poller.

        Args:
            message_processor: The message processor to handle messages
            state_file: Path to file storing the last processed message ID
        """
        self.message_processor = message_processor
        self.state_file = Path(state_file)
        self.api_token = settings.groupme_api_token
        self.group_id = settings.groupme_group_id
        self.api_url = f"https://api.groupme.com/v3/groups/{self.group_id}/messages"

        # Ensure state directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized GroupMePoller for group {self.group_id}")

    def _load_last_message_id(self) -> str | None:
        """
        Load the last processed message ID from state file.

        Returns:
            The last message ID, or None if not found
        """
        try:
            if self.state_file.exists():
                last_id = self.state_file.read_text().strip()
                logger.info(f"Loaded last message ID: {last_id}")
                return last_id
            else:
                logger.info("No previous message ID found, starting fresh")
                return None
        except Exception as e:
            logger.error(f"Error loading last message ID: {e}")
            return None

    def _save_last_message_id(self, message_id: str) -> None:
        """
        Save the last processed message ID to state file.

        Args:
            message_id: The message ID to save
        """
        try:
            self.state_file.write_text(message_id)
            logger.debug(f"Saved last message ID: {message_id}")
        except Exception as e:
            logger.error(f"Error saving last message ID: {e}")

    def _fetch_messages(self, limit: int = 100, before_id: str | None = None) -> list[dict[str, Any]]:
        """
        Fetch messages from GroupMe API.

        Args:
            limit: Maximum number of messages to fetch (default 100, max 100)
            before_id: Fetch messages before this message ID (for pagination)

        Returns:
            List of message dictionaries from GroupMe API

        Raises:
            requests.RequestException: If the API request fails
        """
        params = {
            "token": self.api_token,
            "limit": min(limit, 100),  # GroupMe max is 100
        }

        if before_id:
            params["before_id"] = before_id

        logger.debug(f"Fetching messages from GroupMe (limit={limit}, before_id={before_id})")

        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            if data.get("meta", {}).get("code") != 200:
                logger.error(f"GroupMe API error: {data}")
                raise requests.RequestException(f"GroupMe API returned code {data.get('meta', {}).get('code')}")

            messages = data.get("response", {}).get("messages", [])
            logger.info(f"Fetched {len(messages)} messages from GroupMe")

            return messages

        except requests.RequestException as e:
            logger.error(f"Error fetching messages from GroupMe: {e}")
            raise

    def _process_message_dict(self, message_data: dict[str, Any]) -> dict:
        """
        Convert GroupMe API message format to GroupMeMessage and process it.

        Args:
            message_data: Message data from GroupMe API

        Returns:
            Processing result dictionary
        """
        # Skip system messages
        if message_data.get("system", False):
            logger.debug(f"Skipping system message: {message_data.get('id')}")
            return {"status": "ignored", "reason": "system message"}

        # Skip bot messages (avoid loops)
        if message_data.get("sender_type") == "bot":
            logger.debug(f"Skipping bot message: {message_data.get('id')}")
            return {"status": "ignored", "reason": "bot message"}

        # Convert to GroupMeMessage model
        try:
            message = GroupMeMessage(
                sender_name=message_data.get("name", "Unknown"),
                message_text=message_data.get("text", ""),
                timestamp=message_data.get("created_at", 0),
                group_id=message_data.get("group_id", ""),
                message_id=message_data.get("id", ""),
                sender_id=message_data.get("sender_id", ""),
                preview=False,  # Poller doesn't use preview mode
            )
        except Exception as e:
            logger.error(f"Error parsing message data: {e}")
            return {"status": "error", "reason": f"Invalid message data: {e}"}

        # Process the message through the message processor
        logger.info(f"Processing message {message.message_id} from {message.sender_name}")
        result = self.message_processor.process_message(message)

        return result

    def poll(self, limit: int = 20) -> dict[str, Any]:
        """
        Poll GroupMe for new messages and process them.

        This method:
        1. Loads the last processed message ID
        2. Fetches recent messages from GroupMe
        3. Processes messages newer than the last processed ID
        4. Updates the last processed message ID

        Args:
            limit: Maximum number of messages to fetch (default 20)

        Returns:
            Dictionary with polling results including:
            - messages_fetched: Number of messages retrieved
            - messages_processed: Number of messages actually processed
            - messages_ignored: Number of messages ignored
            - last_message_id: The ID of the most recent message seen
            - results: List of processing results for each message
        """
        logger.info("=" * 60)
        logger.info(f"Starting poll at {datetime.now().isoformat()}")

        # Load last processed message ID
        last_message_id = self._load_last_message_id()

        # Fetch recent messages
        try:
            messages = self._fetch_messages(limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages_fetched": 0,
                "messages_processed": 0,
            }

        if not messages:
            logger.info("No messages retrieved from GroupMe")
            return {
                "success": True,
                "messages_fetched": 0,
                "messages_processed": 0,
                "messages_ignored": 0,
            }

        # GroupMe returns messages in reverse chronological order (newest first)
        # We need to process them oldest to newest to maintain order
        messages.reverse()

        # Filter out messages we've already seen
        new_messages = []
        for msg in messages:
            msg_id = msg.get("id")
            if last_message_id and msg_id <= last_message_id:
                logger.debug(f"Skipping already-processed message: {msg_id}")
                continue
            new_messages.append(msg)

        logger.info(f"Found {len(new_messages)} new messages out of {len(messages)} fetched")

        # Process new messages
        results = []
        processed_count = 0
        ignored_count = 0

        for message_data in new_messages:
            msg_id = message_data.get("id")
            logger.info(f"Processing message {msg_id}")

            result = self._process_message_dict(message_data)
            results.append({
                "message_id": msg_id,
                "result": result,
            })

            if result.get("processed", False):
                processed_count += 1
            else:
                ignored_count += 1

            # Update last message ID after each message
            last_message_id = msg_id
            self._save_last_message_id(msg_id)

        logger.info(f"Poll complete: {len(new_messages)} new, {processed_count} processed, {ignored_count} ignored")
        logger.info("=" * 60)

        return {
            "success": True,
            "messages_fetched": len(messages),
            "messages_new": len(new_messages),
            "messages_processed": processed_count,
            "messages_ignored": ignored_count,
            "last_message_id": last_message_id,
            "results": results,
        }

    def reset_state(self) -> None:
        """
        Reset the poller state by deleting the last message ID.

        Use this to reprocess all messages or start fresh.
        """
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info("Reset poller state - deleted last message ID")
        else:
            logger.info("No state to reset")
