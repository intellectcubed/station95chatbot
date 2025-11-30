"""Data models for the chatbot."""

from typing import Literal
from pydantic import BaseModel, Field


class ShiftInterpretation(BaseModel):
    """Represents the AI's interpretation of a shift change message."""

    is_shift_request: bool = Field(description="Whether this message is about a shift change")
    action: Literal["noCrew", "addShift", "obliterateShift"] | None = Field(
        description="The action to take"
    )
    squad: Literal[34, 35, 42, 43, 54] | None = Field(description="The squad number")
    date: str = Field(description="Date in YYYYMMDD format")
    shift_start: str = Field(description="Shift start time in HHMM format")
    shift_end: str = Field(description="Shift end time in HHMM format")
    confidence: int = Field(ge=0, le=100, description="Confidence score 0-100")
    reasoning: str = Field(description="Explanation of the interpretation")


class CalendarCommand(BaseModel):
    """Represents a command to send to the calendar service."""

    action: Literal["noCrew", "addShift", "obliterateShift"]
    date: str = Field(pattern=r"^\d{8}$", description="Date in YYYYMMDD format")
    shift_start: str = Field(pattern=r"^\d{4}$", description="Start time in HHMM format")
    shift_end: str = Field(pattern=r"^\d{4}$", description="End time in HHMM format")
    squad: Literal[34, 35, 42, 43, 54]
    preview: bool = False  # Preview mode flag

    def to_query_params(self) -> dict[str, str]:
        """Convert to query parameters for HTTP request."""
        return {
            "action": self.action,
            "date": self.date,
            "shift_start": self.shift_start,
            "shift_end": self.shift_end,
            "squad": str(self.squad),
            "preview": str(self.preview),
        }


class GroupMeMessage(BaseModel):
    """Represents a GroupMe message from webhook."""

    sender_name: str
    message_text: str
    timestamp: int
    group_id: str
    message_id: str
    sender_id: str
    preview: bool = False  # Preview mode flag from webhook
