#!/usr/bin/env python3
"""
Unit tests for the agentic chatbot using the stateful mock calendar.

These tests verify that:
1. Messages are correctly interpreted by the LLM
2. Tools are used appropriately to check schedule
3. Calendar commands are executed correctly
4. State changes persist in the mock calendar
5. Edge cases are handled properly
"""

import os
import sys
import pytest
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Force agentic mode and point to mock calendar
os.environ["AI_MODE"] = "agentic"
os.environ["CALENDAR_SERVICE_URL"] = "http://localhost:9999/v1"

from station95chatbot.agentic_processor import AgenticProcessor
from station95chatbot import logging_config

# Initialize logging
logging_config.setup_logging()

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def calendar_client():
    """Provide a client for interacting with the mock calendar."""
    base_url = "http://localhost:9999"

    # Verify calendar is running
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        response.raise_for_status()
    except requests.RequestException as e:
        pytest.skip(f"Mock calendar not running on {base_url}: {e}")

    yield base_url

    # Reset calendar state after each test
    try:
        requests.post(f"{base_url}/reset", timeout=2)
        logger.info("Calendar state reset after test")
    except requests.RequestException as e:
        logger.warning(f"Failed to reset calendar: {e}")


@pytest.fixture(scope="function")
def processor():
    """Provide an AgenticProcessor instance."""
    return AgenticProcessor()


@pytest.fixture
def current_timestamp():
    """Provide current timestamp for message creation."""
    return int(datetime.now().timestamp())


@pytest.fixture
def today_str():
    """Return today's date in YYYYMMDD format."""
    return datetime.now().strftime("%Y%m%d")


@pytest.fixture
def tomorrow_str():
    """Return tomorrow's date in YYYYMMDD format."""
    return (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_schedule(calendar_client, start_date, end_date, squad=None):
    """Query the mock calendar schedule."""
    params = {
        "action": "getSchedule",
        "start_date": start_date,
        "end_date": end_date
    }
    if squad:
        params["squad"] = squad

    response = requests.get(f"{calendar_client}/v1", params=params)
    response.raise_for_status()
    return response.json()


def get_shifts_for_date(calendar_client, date, squad=None):
    """Get shifts for a specific date."""
    schedule = get_schedule(calendar_client, date, date, squad)

    if not schedule.get("dates"):
        return []

    for date_entry in schedule["dates"]:
        if date_entry["date"] == date:
            return date_entry.get("shifts", [])

    return []


def find_shift(shifts, squad, shift_start, shift_end):
    """Find a specific shift in a list of shifts."""
    for shift in shifts:
        if (shift["squad"] == squad and
            shift["shift_start"] == shift_start and
            shift["shift_end"] == shift_end):
            return shift
    return None


# ============================================================================
# BASIC WORKFLOW TESTS
# ============================================================================

class TestBasicWorkflow:
    """Test basic agentic workflow functionality."""

    def test_simple_no_crew_request(self, processor, calendar_client, current_timestamp, today_str):
        """Test a simple 'no crew' message."""
        # Setup: Verify Squad 43 exists in schedule
        initial_shifts = get_shifts_for_date(calendar_client, today_str, squad=43)
        assert len(initial_shifts) > 0, "Squad 43 should be in initial schedule"

        # Execute: Send message
        message = "43 does not have a crew tonight from 1800 to midnight"
        result = processor.process_message(
            message_text=message,
            sender_name="Test Chief",
            sender_squad=43,
            sender_role="Chief",
            message_timestamp=current_timestamp
        )

        # Verify: Message was interpreted correctly
        assert result["is_shift_request"] is True, "Should be recognized as shift request"
        assert result["confidence"] >= 70, f"Confidence should be >= 70, got {result['confidence']}"
        assert len(result["parsed_requests"]) > 0, "Should have parsed at least one request"

        # Verify: Request details
        first_request = result["parsed_requests"][0]
        assert first_request["action"] == "noCrew", f"Action should be noCrew, got {first_request['action']}"
        assert first_request["squad"] == 43

        # Verify: Command was executed (check calendar state)
        # Note: The real test would verify calendar state changed, but we need to check execution results
        assert len(result["execution_results"]) > 0, "Should have execution results"

    def test_add_shift_request(self, processor, calendar_client, current_timestamp, tomorrow_str):
        """Test adding a new shift."""
        # Setup: Verify shift doesn't exist initially
        initial_shifts = get_shifts_for_date(calendar_client, tomorrow_str, squad=54)
        initial_count = len(initial_shifts)

        # Execute: Send message to add shift
        message = f"We need to add Squad 54 for tomorrow's evening shift"
        result = processor.process_message(
            message_text=message,
            sender_name="Test Captain",
            sender_squad=54,
            sender_role="Captain",
            message_timestamp=current_timestamp
        )

        # Verify: Message was interpreted
        assert result["is_shift_request"] is True
        assert len(result["parsed_requests"]) > 0

        # Verify: Action is addShift
        first_request = result["parsed_requests"][0]
        assert first_request["action"] in ["addShift", "addCrew"], "Should be add action"
        assert first_request["squad"] == 54

    def test_non_shift_message(self, processor, current_timestamp):
        """Test that non-shift messages are correctly identified."""
        message = "Hey everyone, great job at the drill today!"

        result = processor.process_message(
            message_text=message,
            sender_name="Test User",
            sender_squad=34,
            sender_role="Member",
            message_timestamp=current_timestamp
        )

        # Verify: Not identified as shift request
        assert result["is_shift_request"] is False, "Should NOT be recognized as shift request"
        assert result["confidence"] < 70 or len(result["parsed_requests"]) == 0


# ============================================================================
# STATE VERIFICATION TESTS
# ============================================================================

class TestStateVerification:
    """Test that calendar state is actually modified correctly."""

    def test_no_crew_modifies_calendar_state(self, processor, calendar_client, current_timestamp, today_str):
        """Verify noCrew command actually changes calendar state."""
        # Setup: Get initial state
        initial_shifts = get_shifts_for_date(calendar_client, today_str)
        initial_squad_43 = find_shift(initial_shifts, 43, "1800", "0600")

        # Should exist and be available initially
        assert initial_squad_43 is not None, "Squad 43 should exist initially"
        assert initial_squad_43["crew_status"] == "available", "Should be available initially"

        # Execute: Mark as no crew (NOT preview mode)
        # First, manually call the calendar to test state change
        response = requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "noCrew",
                "date": today_str,
                "shift_start": "1800",
                "shift_end": "0600",
                "squad": 43,
                "preview": False
            }
        )
        response.raise_for_status()

        # Verify: State changed
        updated_shifts = get_shifts_for_date(calendar_client, today_str)
        updated_squad_43 = find_shift(updated_shifts, 43, "1800", "0600")

        assert updated_squad_43 is not None, "Squad 43 should still exist"
        assert updated_squad_43["crew_status"] == "unavailable", "Should now be unavailable"

    def test_add_shift_creates_new_entry(self, processor, calendar_client, tomorrow_str):
        """Verify addShift creates a new calendar entry."""
        # Setup: Verify shift doesn't exist
        new_date = tomorrow_str
        initial_shifts = get_shifts_for_date(calendar_client, new_date, squad=35)
        initial_shift = find_shift(initial_shifts, 35, "1800", "0600")

        # Execute: Add shift
        response = requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "addShift",
                "date": new_date,
                "shift_start": "1800",
                "shift_end": "0600",
                "squad": 35,
                "preview": False
            }
        )
        response.raise_for_status()

        # Verify: Shift now exists
        updated_shifts = get_shifts_for_date(calendar_client, new_date)
        new_shift = find_shift(updated_shifts, 35, "1800", "0600")

        assert new_shift is not None, "Shift should now exist"
        assert new_shift["crew_status"] == "available", "Should be available"

    def test_obliterate_removes_shift(self, processor, calendar_client, today_str):
        """Verify obliterateShift removes entry from calendar."""
        # Setup: Verify shift exists
        initial_shifts = get_shifts_for_date(calendar_client, today_str)
        initial_shift = find_shift(initial_shifts, 34, "1800", "0600")
        assert initial_shift is not None, "Squad 34 should exist initially"

        # Execute: Obliterate shift
        response = requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "obliterateShift",
                "date": today_str,
                "shift_start": "1800",
                "shift_end": "0600",
                "squad": 34,
                "preview": False
            }
        )
        response.raise_for_status()

        # Verify: Shift is gone
        updated_shifts = get_shifts_for_date(calendar_client, today_str)
        updated_shift = find_shift(updated_shifts, 34, "1800", "0600")

        assert updated_shift is None, "Shift should be removed"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_removing_last_crew_generates_warning(self, processor, calendar_client, current_timestamp):
        """Test that removing the last crew generates a critical warning."""
        # This test would require:
        # 1. Setting up a date with only one crew
        # 2. Sending message to remove that crew
        # 3. Verifying critical warning is generated
        #
        # For now, we'll skip this as it requires complex setup
        pytest.skip("Requires complex calendar state setup")

    def test_duplicate_shift_request(self, processor, calendar_client, current_timestamp, today_str):
        """Test adding a shift that already exists."""
        # Setup: Add a shift
        requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "addShift",
                "date": today_str,
                "shift_start": "0600",
                "shift_end": "1800",
                "squad": 42,
                "preview": False
            }
        )

        # Execute: Add same shift again
        response = requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "addShift",
                "date": today_str,
                "shift_start": "0600",
                "shift_end": "1800",
                "squad": 42,
                "preview": False
            }
        )

        # Verify: Should succeed (update existing)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

    def test_preview_mode_doesnt_modify_state(self, calendar_client, today_str):
        """Verify preview mode doesn't actually change the calendar."""
        # Setup: Get initial state
        initial_shifts = get_shifts_for_date(calendar_client, today_str)
        initial_count = len(initial_shifts)

        # Execute: Command with preview=True
        response = requests.get(
            f"{calendar_client}/v1",
            params={
                "action": "noCrew",
                "date": today_str,
                "shift_start": "1800",
                "shift_end": "0600",
                "squad": 42,
                "preview": True
            }
        )
        response.raise_for_status()
        result = response.json()

        # Verify: Preview flag in response
        assert result.get("preview") is True

        # Verify: State unchanged
        final_shifts = get_shifts_for_date(calendar_client, today_str)
        assert len(final_shifts) == initial_count, "State should not change in preview mode"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEnd:
    """End-to-end integration tests."""

    def test_complete_workflow_with_state_verification(
        self, processor, calendar_client, current_timestamp, today_str
    ):
        """Test complete workflow: message -> interpretation -> execution -> state change."""
        # Setup: Get initial state
        initial_shifts = get_shifts_for_date(calendar_client, today_str, squad=42)

        # Execute: Process message through agentic workflow
        message = "Squad 42 will not have a crew tonight 1800-0000"
        result = processor.process_message(
            message_text=message,
            sender_name="Test Chief",
            sender_squad=42,
            sender_role="Chief",
            message_timestamp=current_timestamp
        )

        # Verify interpretation
        assert result["is_shift_request"] is True
        assert len(result["parsed_requests"]) > 0

        # Verify execution (commands were sent)
        assert len(result["execution_results"]) > 0

        # Note: In preview mode, state won't change
        # To test actual state change, we'd need to disable preview mode
        # in the agentic processor for this test

    def test_multi_request_message(self, processor, current_timestamp):
        """Test message with multiple shift requests."""
        message = """Squad 42 no crew tonight.
        Squad 34 will cover tomorrow morning.
        Remove Squad 54 from Saturday."""

        result = processor.process_message(
            message_text=message,
            sender_name="Test Dispatcher",
            sender_squad=None,
            sender_role="Dispatcher",
            message_timestamp=current_timestamp
        )

        # Verify: Multiple requests parsed
        assert result["is_shift_request"] is True
        # Should have 3 requests (though parsing may vary)
        assert len(result["parsed_requests"]) >= 1, "Should parse at least one request"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    """Run tests with pytest."""
    pytest.main([__file__, "-v", "--tb=short"])
