"""LangChain tools for the agentic AI workflow."""

import logging
from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool

from .calendar_client import CalendarClient
from .config import settings

logger = logging.getLogger(__name__)

# Initialize calendar client
calendar_client = CalendarClient()


@tool
def get_schedule(
    start_date: Annotated[str, "Start date in YYYYMMDD format"],
    end_date: Annotated[str, "End date in YYYYMMDD format"],
    squad: Annotated[int | None, "Optional squad number to filter by (34, 35, 42, 43, or 54)"] = None
) -> dict:
    """
    Fetch the current schedule from the calendar service for a date range.
    Use this to check what shifts are currently scheduled.

    Args:
        start_date: Start date in YYYYMMDD format (e.g., "20251203")
        end_date: End date in YYYYMMDD format (e.g., "20251210")
        squad: Optional squad number to filter by

    Returns:
        Dictionary with schedule data containing dates and shifts
    """
    logger.info(f"🔍 Tool: get_schedule({start_date}, {end_date}, squad={squad})")

    try:
        schedule = calendar_client.get_schedule(start_date, end_date, squad)
        logger.info(f"✅ Schedule fetched successfully")
        return schedule
    except Exception as e:
        error_msg = f"Failed to fetch schedule: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


@tool
def check_squad_scheduled(
    squad: Annotated[int, "Squad number (34, 35, 42, 43, or 54)"],
    date: Annotated[str, "Date in YYYYMMDD format"],
    shift_start: Annotated[str, "Shift start time in HHMM format"],
    shift_end: Annotated[str, "Shift end time in HHMM format"]
) -> bool:
    """
    Check if a specific squad is currently scheduled for a specific shift.

    Args:
        squad: Squad number
        date: Date in YYYYMMDD format
        shift_start: Shift start time in HHMM format (e.g., "1800")
        shift_end: Shift end time in HHMM format (e.g., "0600")

    Returns:
        True if the squad is scheduled for this shift, False otherwise
    """
    logger.info(f"✅ Tool: check_squad_scheduled(squad={squad}, date={date}, {shift_start}-{shift_end})")

    try:
        schedule = calendar_client.get_schedule(date, date, squad)

        # Parse the schedule to check if this specific shift exists
        # Note: The actual structure depends on your calendar API response
        # This is a sample implementation - adjust based on your API
        if "dates" in schedule:
            for date_entry in schedule["dates"]:
                if date_entry.get("date") == date:
                    for shift in date_entry.get("shifts", []):
                        if (shift.get("squad") == squad and
                            shift.get("shift_start") == shift_start and
                            shift.get("shift_end") == shift_end and
                            shift.get("crew_status") == "available"):
                            logger.info(f"✅ Squad {squad} IS scheduled")
                            return True

        logger.info(f"❌ Squad {squad} is NOT scheduled")
        return False

    except Exception as e:
        logger.error(f"Error checking squad schedule: {e}")
        return False


@tool
def count_active_crews(
    date: Annotated[str, "Date in YYYYMMDD format"],
    shift_start: Annotated[str, "Shift start time in HHMM format"],
    shift_end: Annotated[str, "Shift end time in HHMM format"],
    excluding_squad: Annotated[int | None, "Squad to exclude from count (for simulation)"] = None
) -> int:
    """
    Count how many crews will be active/available during a specific shift.
    Use this to check if removing a crew would leave the station out of service.

    Args:
        date: Date in YYYYMMDD format
        shift_start: Shift start time in HHMM format
        shift_end: Shift end time in HHMM format
        excluding_squad: Squad to exclude from count (useful for checking "what if we remove this squad")

    Returns:
        Number of active crews during this time period
    """
    logger.info(
        f"🔢 Tool: count_active_crews(date={date}, {shift_start}-{shift_end}, "
        f"excluding={excluding_squad})"
    )

    try:
        schedule = calendar_client.get_schedule(date, date)

        count = 0
        if "dates" in schedule:
            for date_entry in schedule["dates"]:
                if date_entry.get("date") == date:
                    for shift in date_entry.get("shifts", []):
                        # Check if shift overlaps with requested time period
                        if (shift.get("shift_start") == shift_start and
                            shift.get("shift_end") == shift_end and
                            shift.get("crew_status") == "available" and
                            shift.get("squad") != excluding_squad):
                            count += 1

        logger.info(f"✅ Count: {count} active crews")
        return count

    except Exception as e:
        logger.error(f"Error counting active crews: {e}")
        return 0


@tool
def parse_time_reference(
    time_reference: Annotated[str, "Natural language time reference (e.g., 'tonight', 'Saturday morning')"],
    current_timestamp: Annotated[int, "Current Unix timestamp for reference"]
) -> dict:
    """
    Parse natural language time references into structured date and time data.

    Args:
        time_reference: Natural language time reference
        current_timestamp: Current Unix timestamp for context

    Returns:
        Dictionary with parsed date, shift_start, and shift_end
    """
    logger.info(f"📅 Tool: parse_time_reference('{time_reference}', {current_timestamp})")

    # Convert timestamp to datetime
    current_time = datetime.fromtimestamp(current_timestamp)
    current_date = current_time.strftime("%Y%m%d")

    # Simple parsing logic (can be enhanced)
    result = {
        "date": current_date,
        "shift_start": "1800",  # Default to evening shift
        "shift_end": "0600"
    }

    time_ref_lower = time_reference.lower()

    if "morning" in time_ref_lower:
        result["shift_start"] = "0600"
        result["shift_end"] = "1800"
    elif "evening" in time_ref_lower or "night" in time_ref_lower:
        result["shift_start"] = "1800"
        result["shift_end"] = "0600"

    # Handle day references
    # This is simplified - you might want more sophisticated date parsing
    if "tomorrow" in time_ref_lower:
        from datetime import timedelta
        next_day = current_time + timedelta(days=1)
        result["date"] = next_day.strftime("%Y%m%d")
    elif "saturday" in time_ref_lower:
        # Find next Saturday
        from datetime import timedelta
        days_until_saturday = (5 - current_time.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7  # Next week if today is Saturday
        next_saturday = current_time + timedelta(days=days_until_saturday)
        result["date"] = next_saturday.strftime("%Y%m%d")

    logger.info(f"✅ Parsed: {result}")
    return result


# List of all available tools
all_tools = [
    get_schedule,
    check_squad_scheduled,
    count_active_crews,
    parse_time_reference,
]
