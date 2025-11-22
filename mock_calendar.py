#!/usr/bin/env python3
"""Mock calendar service for testing."""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Mock Calendar Service")

@app.get("/")
async def root():
    return {"status": "ok", "service": "Mock Calendar Service"}

@app.post("/commands")
async def mock_calendar(action: str, date: str, shift_start: str, shift_end: str, squad: int):
    """Mock calendar command endpoint."""
    print(f"\n{'='*80}")
    print(f"📅 Mock Calendar Received Command:")
    print(f"   Action: {action}")
    print(f"   Squad: {squad}")
    print(f"   Date: {date}")
    print(f"   Time: {shift_start} - {shift_end}")
    print(f"{'='*80}\n")

    return {
        "status": "success",
        "message": "Mock calendar updated",
        "command": {
            "action": action,
            "squad": squad,
            "date": date,
            "shift_start": shift_start,
            "shift_end": shift_end
        }
    }

if __name__ == "__main__":
    print("Starting Mock Calendar Service on http://localhost:9999")
    print("Update your .env file:")
    print("  CALENDAR_SERVICE_URL=http://localhost:9999/commands")
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=9999)
