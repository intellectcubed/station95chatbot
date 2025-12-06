#!/usr/bin/env python3
"""
Enhanced mock calendar server for testing agentic AI workflow.

This mock server supports:
- GET /v1?action=getSchedule - Return mock schedule
- GET /v1?action=noCrew/addShift/obliterateShift - Execute commands
"""

from fastapi import FastAPI
from typing import Literal
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Calendar Server")

# Mock schedule data
# In a real system, this would be fetched from a database
MOCK_SCHEDULE = {
    "dates": [
        {
            "date": "20251204",  # Today
            "shifts": [
                {"squad": 34, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
                {"squad": 42, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
                {"squad": 43, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
            ]
        },
        {
            "date": "20251205",  # Tomorrow
            "shifts": [
                {"squad": 35, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
                {"squad": 42, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
            ]
        },
        {
            "date": "20251207",  # Saturday
            "shifts": [
                {"squad": 54, "shift_start": "0600", "shift_end": "1800", "crew_status": "available"},
                {"squad": 34, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
            ]
        }
    ]
}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Mock Calendar Server",
        "version": "1.0",
        "endpoints": {
            "getSchedule": "GET /v1?action=getSchedule&start_date=YYYYMMDD&end_date=YYYYMMDD&squad=XX",
            "noCrew": "GET /v1?action=noCrew&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "addShift": "GET /v1?action=addShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "obliterateShift": "GET /v1?action=obliterateShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX"
        }
    }


@app.get("/v1")
async def handle_request(
    action: Literal["getSchedule", "noCrew", "addShift", "obliterateShift"],
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
    """

    if action == "getSchedule":
        return handle_get_schedule(start_date, end_date, squad)

    elif action in ["noCrew", "addShift", "obliterateShift"]:
        return handle_command(action, date, shift_start, shift_end, squad, preview)

    else:
        return {"error": f"Unknown action: {action}"}


def handle_get_schedule(start_date: str, end_date: str, squad: int | None):
    """Return mock schedule data."""
    logger.info(f"📅 GET SCHEDULE: {start_date} to {end_date}, squad={squad}")

    # Filter schedule by date range
    filtered_dates = []
    for date_entry in MOCK_SCHEDULE["dates"]:
        if start_date <= date_entry["date"] <= end_date:
            # Filter by squad if specified
            if squad is not None:
                shifts = [s for s in date_entry["shifts"] if s["squad"] == squad]
                if shifts:
                    filtered_dates.append({
                        "date": date_entry["date"],
                        "shifts": shifts
                    })
            else:
                filtered_dates.append(date_entry)

    result = {"dates": filtered_dates}
    logger.info(f"✅ Returning {len(filtered_dates)} date(s) with schedule")

    return result


def handle_command(
    action: str,
    date: str,
    shift_start: str,
    shift_end: str,
    squad: int,
    preview: bool
):
    """Handle calendar commands (noCrew, addShift, obliterateShift)."""

    preview_str = "[PREVIEW] " if preview else ""

    logger.info(
        f"📝 {preview_str}COMMAND: {action} - Squad {squad} - "
        f"{date} {shift_start}-{shift_end}"
    )

    # In a real system, this would update the database
    # For mock, we just log and return success

    if action == "noCrew":
        message = f"{preview_str}Marked Squad {squad} as no crew for {date} {shift_start}-{shift_end}"
    elif action == "addShift":
        message = f"{preview_str}Added shift for Squad {squad} on {date} {shift_start}-{shift_end}"
    elif action == "obliterateShift":
        message = f"{preview_str}Obliterated shift for Squad {squad} on {date} {shift_start}-{shift_end}"

    logger.info(f"✅ {message}")

    return {
        "status": "success",
        "action": action,
        "squad": squad,
        "date": date,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "preview": preview,
        "message": message
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-calendar"}


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 STARTING ENHANCED MOCK CALENDAR SERVER")
    print("="*80)
    print("\nThis server supports:")
    print("  ✓ getSchedule - Return mock schedule data")
    print("  ✓ noCrew - Mark crew as unavailable")
    print("  ✓ addShift - Add new shift")
    print("  ✓ obliterateShift - Remove shift")
    print("\n" + "="*80)
    print("Running on: http://localhost:9999")
    print("Set in .env: CALENDAR_SERVICE_URL=http://localhost:9999/v1")
    print("="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=9999, log_level="info")
