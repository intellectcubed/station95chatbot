"""AI/LLM integration for interpreting shift change messages."""

import json
import logging
from datetime import datetime
from typing import Any

from .config import settings
from .models import ShiftInterpretation

logger = logging.getLogger(__name__)


class AIProcessor:
    """Processes messages using AI/LLM to interpret shift requests."""

    def __init__(self):
        """Initialize the AI processor with the configured provider."""
        self.provider = settings.ai_provider
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the appropriate AI client based on configuration."""
        if self.provider == "openai":
            try:
                import openai

                self.client = openai.OpenAI(api_key=settings.openai_api_key)
                logger.info("Initialized OpenAI client")
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        elif self.provider == "anthropic":
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                logger.info("Initialized Anthropic client")
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def _build_prompt(
        self,
        sender_name: str,
        sender_squad: int | None,
        sender_role: str | None,
        message_text: str,
        message_timestamp: int,
    ) -> str:
        """Build the AI prompt for message interpretation."""
        # Use message timestamp as "current date" for consistent interpretation
        # This ensures "tonight", "tomorrow", etc. are relative to when message was sent
        message_time = datetime.fromtimestamp(message_timestamp)
        current_date = message_time.strftime("%Y-%m-%d %H:%M:%S")
        message_time_str = message_time.strftime("%Y-%m-%d %H:%M:%S")

        return f"""You are a rescue squad shift management assistant. Analyze the following GroupMe message and extract shift change information.

**Message Details:**
- Sender: {sender_name}
- Sender's Squad: {sender_squad if sender_squad else "Unknown"}
- Sender's Role: {sender_role if sender_role else "Unknown"}
- Message: "{message_text}"
- Message Sent At: {message_time_str}
- Current Date/Time (use this as "now"): {current_date}

**Your Task:**
Extract and return a JSON object with the following structure:

{{
  "is_shift_request": boolean,
  "action": "noCrew" | "addShift" | "obliterateShift" | null,
  "squad": number (34, 35, 42, 43, or 54),
  "date": "YYYYMMDD",
  "shift_start": "HHMM",
  "shift_end": "HHMM",
  "confidence": number (0-100),
  "reasoning": "Brief explanation of interpretation"
}}

**Rules:**
1. If squad not explicitly mentioned in message, use sender's squad: {sender_squad}
2. If sender mentions another squad explicitly, use that squad instead
3. Interpret colloquial time references:
   - "tonight" = today's evening shift (1800-0600 next day)
   - "tomorrow" = next day
   - "morning" = 0600-1800
   - "afternoon" = 1200-1800 (or use context)
   - "evening" = 1800-0600
   - "Saturday", "Sunday", etc. = next occurrence of that day
4. Weekend shifts are 12 hours: 0600-1800 or 1800-0600
5. Weeknight shifts are 12 hours: 0600-1800 or 1800-0600
6. If specific times are mentioned (e.g., "1800 - midnight"), use those times
7. "midnight" = 0000, "noon" = 1200
8. When a shift spans midnight, the end time (like 0600) refers to the next day

**CRITICAL - Date Interpretation (Always Future Dates):**
- ALL date references are for FUTURE shifts, never past dates
- Current date is: {current_date}
- If a month is mentioned (e.g., "March 15th"), determine if that date has already passed this year:
  * If the date HAS passed this year → use NEXT year
  * If the date has NOT passed yet this year → use THIS year
- Examples (assuming current date is November 22, 2025):
  * "March 15th" → March 15, 2026 (March 2025 has passed)
  * "December 10th" → December 10, 2025 (December 2025 hasn't happened yet)
  * "tonight" → November 22, 2025 evening
  * "Saturday" → next Saturday from current date

**IMPORTANT - Determining is_shift_request:**
- If the message mentions crew availability, staffing, shifts, or schedule changes → is_shift_request: true
- Phrases like "no crew", "does not have a crew", "fully staffed", "crew available" → is_shift_request: true
- If you can extract an action (noCrew, addShift, obliterateShift) → is_shift_request: MUST be true
- Only set is_shift_request: false for casual conversation, greetings, or off-topic messages
- Messages about future dates (like "March 15th") ARE shift requests

Respond ONLY with valid JSON. Do not include any explanation outside the JSON structure."""

    def _call_openai(self, prompt: str) -> dict[str, Any]:
        """Call OpenAI API to interpret the message."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise shift management interpreter. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _call_anthropic(self, prompt: str) -> dict[str, Any]:
        """Call Anthropic API to interpret the message."""
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            # Extract JSON from response (Claude might add text around it)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def interpret_message(
        self,
        sender_name: str,
        sender_squad: int | None,
        sender_role: str | None,
        message_text: str,
        message_timestamp: int,
    ) -> ShiftInterpretation:
        """
        Interpret a message using AI/LLM.

        Returns a ShiftInterpretation object with the extracted information.
        """
        prompt = self._build_prompt(
            sender_name, sender_squad, sender_role, message_text, message_timestamp
        )

        # print(f'Prompt: {prompt}')

        logger.info(f"Interpreting message from {sender_name}: {message_text[:50]}...")

        try:
            if self.provider == "openai":
                result = self._call_openai(prompt)
            elif self.provider == "anthropic":
                result = self._call_anthropic(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            interpretation = ShiftInterpretation(**result)

            # Safety check: if action is set, is_shift_request MUST be true
            if interpretation.action is not None and not interpretation.is_shift_request:
                logger.warning(
                    f"AI contradiction detected: action={interpretation.action} but "
                    f"is_shift_request=False. Correcting to True."
                )
                interpretation.is_shift_request = True

            logger.info(
                f"Interpretation complete: is_shift_request={interpretation.is_shift_request}, "
                f"confidence={interpretation.confidence}"
            )

            return interpretation

        except Exception as e:
            logger.error(f"Error interpreting message: {e}")
            # Return a low-confidence interpretation on error
            return ShiftInterpretation(
                is_shift_request=False,
                action=None,
                squad=sender_squad,
                date="",
                shift_start="",
                shift_end="",
                confidence=0,
                reasoning=f"Error during interpretation: {str(e)}",
            )
