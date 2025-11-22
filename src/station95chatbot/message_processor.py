"""Message processing pipeline for shift change requests."""

import logging
from datetime import datetime

from .ai_processor import AIProcessor
from .calendar_client import CalendarClient
from .config import settings
from .models import CalendarCommand, GroupMeMessage, ShiftInterpretation
from .roster import Roster

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes GroupMe messages and executes shift change commands."""

    def __init__(self, roster: Roster, ai_processor: AIProcessor, calendar_client: CalendarClient):
        """Initialize the message processor."""
        self.roster = roster
        self.ai_processor = ai_processor
        self.calendar_client = calendar_client
        self.confidence_threshold = settings.confidence_threshold

    def should_process_message(self, message: GroupMeMessage) -> bool:
        """
        Determine if a message should be processed.

        Filters out:
        - Messages from non-roster members
        - Messages that don't contain shift-related keywords
        """
        # Check if sender is authorized
        if not self.roster.is_authorized(message.sender_name):
            logger.info(f"Ignoring message from unauthorized user: {message.sender_name}")
            return False

        # Check for shift-related keywords
        keywords = [
            "crew",
            "shift",
            "squad",
            "tonight",
            "tomorrow",
            "morning",
            "afternoon",
            "evening",
            "saturday",
            "sunday",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "staffed",
            "no crew",
        ]

        message_lower = message.message_text.lower()
        has_keywords = any(keyword in message_lower for keyword in keywords)

        if not has_keywords:
            logger.debug(f"Message doesn't contain shift keywords: {message.message_text[:50]}...")
            return False

        return True

    def process_message(self, message: GroupMeMessage) -> dict:
        """
        Process a GroupMe message through the full pipeline.

        Returns a dict with processing results and status.
        """
        logger.info(f"Processing message from {message.sender_name}")

        result = {
            "message_id": message.message_id,
            "sender": message.sender_name,
            "timestamp": datetime.now().isoformat(),
            "processed": False,
            "reason": None,
            "interpretation": None,
            "command_sent": False,
            "error": None,
        }

        try:
            # Check if message should be processed
            if not self.should_process_message(message):
                result["reason"] = "Filtered out (no keywords or unauthorized sender)"
                self._log_to_file(message, None, result)
                return result

            # Get sender information
            sender_squad = self.roster.get_member_squad(message.sender_name)
            sender_role = self.roster.get_member_role(message.sender_name)

            # Interpret the message using AI
            interpretation = self.ai_processor.interpret_message(
                sender_name=message.sender_name,
                sender_squad=sender_squad,
                sender_role=sender_role,
                message_text=message.message_text,
                message_timestamp=message.timestamp,
            )

            result["interpretation"] = interpretation.model_dump()

            # Check if it's a shift request
            if not interpretation.is_shift_request:
                result["reason"] = "Not a shift request"
                self._log_to_file(message, interpretation, result)
                return result

            # Check confidence threshold
            if interpretation.confidence < self.confidence_threshold:
                result["reason"] = (
                    f"Low confidence ({interpretation.confidence} < "
                    f"{self.confidence_threshold})"
                )
                logger.warning(
                    f"Low confidence interpretation: {interpretation.confidence}%. "
                    f"Flagging for manual review."
                )
                self._log_to_file(message, interpretation, result)
                return result

            # Validate that we have all required fields
            if not all(
                [
                    interpretation.action,
                    interpretation.squad,
                    interpretation.date,
                    interpretation.shift_start,
                    interpretation.shift_end,
                ]
            ):
                result["reason"] = "Missing required fields in interpretation"
                self._log_to_file(message, interpretation, result)
                return result

            # Create and send calendar command
            command = CalendarCommand(
                action=interpretation.action,
                squad=interpretation.squad,
                date=interpretation.date,
                shift_start=interpretation.shift_start,
                shift_end=interpretation.shift_end,
            )

            logger.info(f"Executing command: {command.model_dump()}")
            response = self.calendar_client.send_command_with_retry(command)

            result["processed"] = True
            result["command_sent"] = True
            result["calendar_response"] = response
            result["reason"] = "Successfully processed and command sent"

            self._log_to_file(message, interpretation, result)

            logger.info(f"Successfully processed message {message.message_id}")

            return result

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            result["error"] = str(e)
            result["reason"] = f"Error: {str(e)}"
            self._log_to_file(message, None, result)
            return result

    def _log_to_file(
        self,
        message: GroupMeMessage,
        interpretation: ShiftInterpretation | None,
        result: dict,
    ) -> None:
        """Log message processing details to a file for review and improvement."""
        import json
        from pathlib import Path

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"message_log_{datetime.now().strftime('%Y%m%d')}.jsonl"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message.model_dump(),
            "interpretation": interpretation.model_dump() if interpretation else None,
            "result": result,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
