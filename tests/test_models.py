"""Tests for data models."""

import pytest
from pydantic import ValidationError

from src.station95chatbot.models import CalendarCommand, ShiftInterpretation, GroupMeMessage


def test_calendar_command_valid():
    """Test creating a valid calendar command."""
    command = CalendarCommand(
        action="noCrew",
        date="20251110",
        shift_start="1800",
        shift_end="0600",
        squad=42,
    )

    assert command.action == "noCrew"
    assert command.squad == 42

    params = command.to_query_params()
    assert params["action"] == "noCrew"
    assert params["date"] == "20251110"
    assert params["squad"] == "42"


def test_calendar_command_invalid_date():
    """Test that invalid date format raises validation error."""
    with pytest.raises(ValidationError):
        CalendarCommand(
            action="noCrew",
            date="2025-11-10",  # Wrong format
            shift_start="1800",
            shift_end="0600",
            squad=42,
        )


def test_calendar_command_invalid_squad():
    """Test that invalid squad number raises validation error."""
    with pytest.raises(ValidationError):
        CalendarCommand(
            action="noCrew",
            date="20251110",
            shift_start="1800",
            shift_end="0600",
            squad=99,  # Invalid squad
        )


def test_shift_interpretation():
    """Test shift interpretation model."""
    interpretation = ShiftInterpretation(
        is_shift_request=True,
        action="noCrew",
        squad=42,
        date="20251110",
        shift_start="1800",
        shift_end="0600",
        confidence=85,
        reasoning="Message clearly indicates no crew available",
    )

    assert interpretation.is_shift_request is True
    assert interpretation.confidence == 85
    assert interpretation.squad == 42


def test_groupme_message():
    """Test GroupMe message model."""
    message = GroupMeMessage(
        sender_name="George Nowakowski",
        message_text="43 does not have a crew tonight",
        timestamp=1234567890,
        group_id="12345",
        message_id="msg_123",
        sender_id="user_123",
    )

    assert message.sender_name == "George Nowakowski"
    assert "crew" in message.message_text
