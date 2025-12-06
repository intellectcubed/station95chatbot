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

        # Initialize agentic processor if needed
        self.agentic_processor = None
        if settings.ai_mode == "agentic":
            from .agentic_processor import AgenticProcessor
            self.agentic_processor = AgenticProcessor()
            logger.info("Initialized in AGENTIC mode (multi-step workflow)")
        else:
            logger.info("Initialized in SIMPLE mode (single LLM call)")

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
            "covering",
        ]

        message_lower = message.message_text.lower()
        has_keywords = any(keyword in message_lower for keyword in keywords)

        if not has_keywords:
            logger.debug(f"Message doesn't contain shift keywords: {message.message_text[:50]}...")
            # Secondary check: ask AI if this might still be a shift request
            if self._ai_keyword_check(message.message_text):
                logger.info(f"AI detected potential shift request despite no keywords")
                return True
            return False

        return True

    def _ai_keyword_check(self, message_text: str) -> bool:
        """
        Use AI to determine if a message without keywords might still be a shift request.

        Returns True if AI thinks this could be a shift request.
        """
        try:
            # Only do AI check if using OpenAI provider
            if settings.ai_provider != "openai":
                logger.debug("Skipping AI keyword check (not using OpenAI)")
                return False

            import openai

            client = openai.OpenAI(api_key=settings.openai_api_key)

            prompt = f"""You are analyzing messages for a rescue squad shift management system.

Context: This is a rescue squad calendar system where chiefs and members coordinate crew availability for shifts. Squads (34, 35, 42, 43, 54) need to staff 12-hour shifts (typically 0600-1800 or 1800-0600).

Message: "{message_text}"

Question: Does this message seem like a request to add, remove, or modify crew availability for a shift? This could include:
- Reporting that a crew is unavailable
- Confirming crew availability
- Requesting coverage
- Canceling or modifying a scheduled shift
- Any scheduling or staffing issue related to rescue squad shifts

Answer with ONLY "yes" or "no" (lowercase)."""
            
            print('*'*50)
            logger.info(f'Checking with AI to determine if its a shift request Prompt: ')
            logger.info(prompt)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise classifier. Answer only 'yes' or 'no'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )

            answer = response.choices[0].message.content.strip().lower()
            logger.debug(f"AI keyword check for '{message_text[:50]}...': {answer}")
            print(f"AI keyword check for '{message_text[:50]}...': {answer}")
            print('*'*50)


            return answer == "yes"

        except Exception as e:
            logger.warning(f"AI keyword check failed: {e}, defaulting to False")
            return False

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

            # Route to appropriate processor based on mode
            if settings.ai_mode == "agentic" and self.agentic_processor:
                return self._process_agentic(message, sender_squad, sender_role, result)
            else:
                return self._process_simple(message, sender_squad, sender_role, result)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            result["error"] = str(e)
            result["reason"] = f"Error: {str(e)}"
            self._log_to_file(message, None, result)
            return result

    def _process_simple(
        self,
        message: GroupMeMessage,
        sender_squad: int | None,
        sender_role: str | None,
        result: dict
    ) -> dict:
        """
        Process a message using the simple (single LLM call) approach.

        This is the original implementation.
        """
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
            preview=message.preview,  # Pass through preview flag
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

    def _process_agentic(
        self,
        message: GroupMeMessage,
        sender_squad: int | None,
        sender_role: str | None,
        result: dict
    ) -> dict:
        """
        Process a message using the agentic (multi-step workflow) approach.

        This uses LangGraph to orchestrate complex multi-step workflows.
        """
        logger.info(f"Using AGENTIC processing for message: {message.message_text[:50]}...")

        # Call the agentic processor
        agentic_result = self.agentic_processor.process_message(
            message_text=message.message_text,
            sender_name=message.sender_name,
            sender_squad=sender_squad,
            sender_role=sender_role,
            message_timestamp=message.timestamp
        )

        # Map agentic result to standard result format
        result["interpretation"] = {
            "is_shift_request": agentic_result.get("is_shift_request", False),
            "confidence": agentic_result.get("confidence", 0),
            "parsed_requests": agentic_result.get("parsed_requests", []),
            "warnings": agentic_result.get("warnings", []),
            "critical_warnings": agentic_result.get("critical_warnings", []),
        }

        # Check if it's a shift request
        if not agentic_result.get("is_shift_request", False):
            result["reason"] = "Not a shift request"
            self._log_to_file(message, None, result)
            return result

        # Check confidence threshold
        if agentic_result.get("confidence", 0) < self.confidence_threshold:
            result["reason"] = (
                f"Low confidence ({agentic_result.get('confidence')} < "
                f"{self.confidence_threshold})"
            )
            logger.warning(
                f"Low confidence interpretation: {agentic_result.get('confidence')}%. "
                f"Flagging for manual review."
            )
            self._log_to_file(message, None, result)
            return result

        # Check execution results
        execution_results = agentic_result.get("execution_results", [])
        if execution_results:
            result["processed"] = True
            result["command_sent"] = True
            result["execution_results"] = execution_results
            result["warnings"] = agentic_result.get("warnings", [])
            result["critical_warnings"] = agentic_result.get("critical_warnings", [])
            result["reason"] = f"Successfully processed {len(execution_results)} command(s)"

            logger.info(f"Successfully processed message {message.message_id} with {len(execution_results)} commands")
        else:
            result["reason"] = "No commands executed"

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
        import os
        from pathlib import Path

        # Skip file logging in Lambda - use CloudWatch instead
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            logger.debug("Skipping file logging in Lambda (logs go to CloudWatch)")
            return

        # For local/non-Lambda environments, write to logs directory
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
