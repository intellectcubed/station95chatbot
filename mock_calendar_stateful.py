#!/usr/bin/env python3
"""
Stateful mock calendar server for testing the chatbot.

This mock server maintains an in-memory schedule that can be modified
through calendar commands (noCrew, addShift, obliterateShift).

State is consistent during runtime but not persisted between restarts.
"""

from fastapi import FastAPI
from typing import Literal
import uvicorn
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stateful Mock Calendar Server")


class ScheduleState:
    """Maintains the in-memory schedule state."""

    def __init__(self):
        """Initialize with default schedule data."""
        self.schedule = {}  # {date: [shifts]}
        self._initialize_default_schedule()

    def _initialize_default_schedule(self):
        """Set up initial schedule with some default data."""
        today = datetime.now()

        # Today's date
        today_str = today.strftime("%Y%m%d")
        self.schedule[today_str] = [
            {"squad": 34, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
            {"squad": 42, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
            {"squad": 43, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
        ]

        # Tomorrow
        tomorrow = today + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y%m%d")
        self.schedule[tomorrow_str] = [
            {"squad": 35, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
            {"squad": 42, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
        ]

        # Day after tomorrow
        day_after = today + timedelta(days=2)
        day_after_str = day_after.strftime("%Y%m%d")
        self.schedule[day_after_str] = [
            {"squad": 54, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
            {"squad": 34, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
        ]

        logger.info(f"Initialized schedule with {len(self.schedule)} dates")

    def get_schedule(self, start_date: str, end_date: str, squad: int | None = None) -> dict:
        """
        Get schedule for a date range.

        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            squad: Optional squad filter

        Returns:
            Schedule dictionary with dates and shifts
        """
        filtered_dates = []

        # Iterate through all dates in the schedule
        for date, shifts in sorted(self.schedule.items()):
            if start_date <= date <= end_date:
                # Filter by squad if specified
                if squad is not None:
                    filtered_shifts = [s for s in shifts if s["squad"] == squad]
                    if filtered_shifts:
                        filtered_dates.append({
                            "date": date,
                            "shifts": filtered_shifts
                        })
                else:
                    if shifts:  # Only include dates with shifts
                        filtered_dates.append({
                            "date": date,
                            "shifts": shifts.copy()  # Return a copy
                        })

        return {"dates": filtered_dates}

    def add_shift(self, date: str, shift_start: str, shift_end: str, squad: int) -> dict:
        """
        Add a new shift to the schedule.

        Args:
            date: Date in YYYYMMDD format
            shift_start: Shift start time in HHMM format
            shift_end: Shift end time in HHMM format
            squad: Squad number

        Returns:
            Result dictionary
        """
        # Initialize date if it doesn't exist
        if date not in self.schedule:
            self.schedule[date] = []

        # Check if shift already exists
        for shift in self.schedule[date]:
            if (shift["squad"] == squad and
                shift["shift_start"] == shift_start and
                shift["shift_end"] == shift_end):
                # Shift exists - update status to available
                shift["crew_status"] = "available"
                logger.info(f"Updated existing shift to available: Squad {squad} on {date}")
                return {
                    "status": "success",
                    "action": "addShift",
                    "message": f"Updated Squad {squad} to available for {date} {shift_start}-{shift_end}"
                }

        # Add new shift
        new_shift = {
            "squad": squad,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "crew_status": "available"
        }
        self.schedule[date].append(new_shift)
        logger.info(f"Added shift: Squad {squad} on {date} {shift_start}-{shift_end}")

        return {
            "status": "success",
            "action": "addShift",
            "message": f"Added shift for Squad {squad} on {date} {shift_start}-{shift_end}"
        }

    def no_crew(self, date: str, shift_start: str, shift_end: str, squad: int) -> dict:
        """
        Mark a shift as having no crew available.

        Args:
            date: Date in YYYYMMDD format
            shift_start: Shift start time in HHMM format
            shift_end: Shift end time in HHMM format
            squad: Squad number

        Returns:
            Result dictionary
        """
        # Initialize date if it doesn't exist
        if date not in self.schedule:
            self.schedule[date] = []

        # Find existing shift
        for shift in self.schedule[date]:
            if (shift["squad"] == squad and
                shift["shift_start"] == shift_start and
                shift["shift_end"] == shift_end):
                # Found it - mark as unavailable
                shift["crew_status"] = "unavailable"
                logger.info(f"Marked no crew: Squad {squad} on {date}")
                return {
                    "status": "success",
                    "action": "noCrew",
                    "message": f"Marked Squad {squad} as no crew for {date} {shift_start}-{shift_end}"
                }

        # Shift doesn't exist - create it with unavailable status
        new_shift = {
            "squad": squad,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "crew_status": "unavailable"
        }
        self.schedule[date].append(new_shift)
        logger.info(f"Created unavailable shift: Squad {squad} on {date}")

        return {
            "status": "success",
            "action": "noCrew",
            "message": f"Created and marked Squad {squad} as no crew for {date} {shift_start}-{shift_end}"
        }

    def obliterate_shift(self, date: str, shift_start: str, shift_end: str, squad: int) -> dict:
        """
        Completely remove a shift from the schedule.

        Args:
            date: Date in YYYYMMDD format
            shift_start: Shift start time in HHMM format
            shift_end: Shift end time in HHMM format
            squad: Squad number

        Returns:
            Result dictionary
        """
        if date not in self.schedule:
            return {
                "status": "success",
                "action": "obliterateShift",
                "message": f"No shifts found for {date}"
            }

        # Find and remove the shift
        original_count = len(self.schedule[date])
        self.schedule[date] = [
            shift for shift in self.schedule[date]
            if not (shift["squad"] == squad and
                   shift["shift_start"] == shift_start and
                   shift["shift_end"] == shift_end)
        ]

        removed_count = original_count - len(self.schedule[date])

        if removed_count > 0:
            logger.info(f"Obliterated shift: Squad {squad} on {date}")
            return {
                "status": "success",
                "action": "obliterateShift",
                "message": f"Obliterated shift for Squad {squad} on {date} {shift_start}-{shift_end}"
            }
        else:
            return {
                "status": "success",
                "action": "obliterateShift",
                "message": f"Shift not found for Squad {squad} on {date} {shift_start}-{shift_end}"
            }

    def get_schedule_day(self, date: str) -> dict:
        """
        Get schedule for a single day.

        Args:
            date: Date in YYYYMMDD format

        Returns:
            Dictionary with shifts for the specified date
        """
        if date in self.schedule:
            return {
                "date": date,
                "shifts": self.schedule[date].copy()
            }
        else:
            return {
                "date": date,
                "shifts": []
            }

    def reset_to_defaults(self):
        """Reset schedule to default state."""
        self.schedule.clear()
        self._initialize_default_schedule()
        logger.info("Schedule reset to defaults")


# Global schedule state
schedule_state = ScheduleState()


@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "service": "Stateful Mock Calendar Server",
        "version": "2.0",
        "description": "In-memory stateful calendar for testing",
        "endpoints": {
            "getSchedule": "GET /v1?action=getSchedule&start_date=YYYYMMDD&end_date=YYYYMMDD&squad=XX",
            "get_schedule_day": "GET /v1?action=get_schedule_day&date=YYYYMMDD",
            "noCrew": "GET /v1?action=noCrew&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "addShift": "GET /v1?action=addShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "obliterateShift": "GET /v1?action=obliterateShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "reset": "POST /reset (resets schedule to defaults)"
        }
    }


@app.get("/v1")
async def handle_request(
    action: Literal["getSchedule", "get_schedule_day", "noCrew", "addShift", "obliterateShift"],
    start_date: str | None = None,
    end_date: str | None = None,
    date: str | None = None,
    shift_start: str | None = None,
    shift_end: str | None = None,
    squad: int | None = None,
    preview: bool = False
):
    """
    Handle all calendar requests (both queries and commands).

    Args:
        action: The action to perform
        start_date: Start date for getSchedule (YYYYMMDD)
        end_date: End date for getSchedule (YYYYMMDD)
        date: Date for commands (YYYYMMDD)
        shift_start: Shift start time (HHMM)
        shift_end: Shift end time (HHMM)
        squad: Squad number
        preview: If True, don't modify state (just return what would happen)
    """
    logger.info(f"📥 Request: action={action}, date={date or start_date}, squad={squad}, preview={preview}")

    if action == "getSchedule":
        if not start_date or not end_date:
            return {"error": "start_date and end_date are required for getSchedule"}

        result = schedule_state.get_schedule(start_date, end_date, squad)
        logger.info(f"✅ Returning schedule with {len(result['dates'])} date(s)")
        return result

    elif action == "get_schedule_day":
        if not date:
            return {"error": "date is required for get_schedule_day"}

        result = schedule_state.get_schedule_day(date)
        logger.info(f"✅ Returning schedule for {date} with {len(result['shifts'])} shift(s)")
        return result

    elif action == "noCrew":
        if not all([date, shift_start, shift_end, squad]):
            return {"error": "date, shift_start, shift_end, and squad are required for noCrew"}

        if preview:
            logger.info(f"🔍 PREVIEW: Would mark Squad {squad} as no crew")
            return {
                "status": "success",
                "action": "noCrew",
                "preview": True,
                "message": f"[PREVIEW] Would mark Squad {squad} as no crew for {date} {shift_start}-{shift_end}"
            }

        return schedule_state.no_crew(date, shift_start, shift_end, squad)

    elif action == "addShift":
        if not all([date, shift_start, shift_end, squad]):
            return {"error": "date, shift_start, shift_end, and squad are required for addShift"}

        if preview:
            logger.info(f"🔍 PREVIEW: Would add shift for Squad {squad}")
            return {
                "status": "success",
                "action": "addShift",
                "preview": True,
                "message": f"[PREVIEW] Would add shift for Squad {squad} on {date} {shift_start}-{shift_end}"
            }

        return schedule_state.add_shift(date, shift_start, shift_end, squad)

    elif action == "obliterateShift":
        if not all([date, shift_start, shift_end, squad]):
            return {"error": "date, shift_start, shift_end, and squad are required for obliterateShift"}

        if preview:
            logger.info(f"🔍 PREVIEW: Would obliterate shift for Squad {squad}")
            return {
                "status": "success",
                "action": "obliterateShift",
                "preview": True,
                "message": f"[PREVIEW] Would obliterate shift for Squad {squad} on {date} {shift_start}-{shift_end}"
            }

        return schedule_state.obliterate_shift(date, shift_start, shift_end, squad)

    else:
        return {"error": f"Unknown action: {action}"}


@app.post("/reset")
async def reset_schedule():
    """Reset the schedule to default state."""
    schedule_state.reset_to_defaults()
    return {
        "status": "success",
        "message": "Schedule reset to defaults",
        "dates": len(schedule_state.schedule)
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "stateful-mock-calendar",
        "dates_in_schedule": len(schedule_state.schedule)
    }


@app.get("/debug/state")
async def debug_state():
    """Debug endpoint to view current state."""
    return {
        "total_dates": len(schedule_state.schedule),
        "schedule": schedule_state.schedule
    }


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 STARTING STATEFUL MOCK CALENDAR SERVER")
    print("="*80)
    print("\nThis server maintains in-memory state and supports:")
    print("  ✓ getSchedule - Query current schedule")
    print("  ✓ noCrew - Mark crew as unavailable (modifies state)")
    print("  ✓ addShift - Add new shift (modifies state)")
    print("  ✓ obliterateShift - Remove shift (modifies state)")
    print("  ✓ POST /reset - Reset to default schedule")
    print("  ✓ GET /debug/state - View current state")
    print("\n" + "="*80)
    print("Running on: http://localhost:9999")
    print("Set in .env: CALENDAR_SERVICE_URL=http://localhost:9999/v1")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=9999, log_level="info")
