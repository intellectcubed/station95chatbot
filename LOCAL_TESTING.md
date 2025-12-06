# Local Testing Guide

This guide explains how to test the Station 95 ChatBot locally using different approaches.

## Table of Contents

1. [Option 1: Live Testing with ngrok + GroupMe](#option-1-live-testing-with-ngrok--groupme)
2. [Option 2: Simulated Testing (No GroupMe)](#option-2-simulated-testing-no-groupme)
3. [Option 3: Unit Testing](#option-3-unit-testing)
4. [Option 4: Testing Agentic AI Workflow](#option-4-testing-agentic-ai-workflow)
5. [Setting Up Mock Calendar Server](#setting-up-mock-calendar-server)
6. [Debugging Tips](#debugging-tips)

---

## Option 1: Live Testing with ngrok + GroupMe

This approach connects your local development server to the real GroupMe service, allowing you to receive and process actual messages.

### What is ngrok?

ngrok creates a secure tunnel from the internet to your localhost. When GroupMe sends a webhook, it goes:

```
GroupMe Server → ngrok.io URL → ngrok tunnel → Your localhost:8080
```

### Setup Steps

#### 1. Install ngrok

**macOS:**
```bash
brew install ngrok
```

**Other platforms:**
Download from https://ngrok.com/download

#### 2. Start Your Bot Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Start the bot (runs on port 8080 by default)
python run.py
```

You should see:
```
INFO: Starting webhook server on 0.0.0.0:8080
INFO: Uvicorn running on http://0.0.0.0:8080
```

#### 3. Start ngrok Tunnel

Open a **new terminal window** and run:

```bash
ngrok http 8080
```

You'll see output like:
```
ngrok

Session Status                online
Account                       your-account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8080
```

**Copy the HTTPS forwarding URL** (e.g., `https://abc123.ngrok.io`)

#### 4. Configure GroupMe Bot Webhook

1. Go to https://dev.groupme.com/bots
2. Find your bot and click "Edit"
3. Set the **Callback URL** to: `https://abc123.ngrok.io/webhook`
4. Save changes

#### 5. Test with Real Messages

Now send messages in your GroupMe chat and watch your terminal logs!

**Example test message:**
```
"43 does not have a crew tonight from 1800 to midnight"
```

**What happens:**
1. Message sent in GroupMe
2. GroupMe sends webhook to ngrok URL
3. ngrok forwards to your localhost:8080
4. Your bot processes the message
5. AI interprets the message
6. Calendar command is sent (if confidence > 70%)

#### 6. Monitor in Real-Time

You can monitor all requests in the **ngrok web interface**:
- Open http://127.0.0.1:4040 in your browser
- See all incoming webhooks and responses
- Replay requests for debugging

### Important Notes

- ⚠️ **ngrok URLs change** every time you restart ngrok (free plan)
- ⚠️ You must **update the GroupMe webhook URL** each time you restart ngrok
- ⚠️ **Real messages** will trigger real calendar updates!
- ✅ Use a **test GroupMe group** to avoid affecting production calendars

### ngrok Pro Tip

Get a permanent URL with a free ngrok account:

```bash
# Sign up at ngrok.com and get your authtoken
ngrok config add-authtoken YOUR_TOKEN

# Use a custom subdomain (requires paid plan)
ngrok http 8080 --subdomain=station95-dev
```

---

## Option 2: Simulated Testing (No GroupMe)

This approach lets you test the bot **without connecting to GroupMe** by sending fake webhook payloads directly to your local server.

### Setup Steps

#### 1. Start Your Bot Locally

```bash
source venv/bin/activate
python run.py
```

#### 2. Send Mock Webhook Requests

You can use `curl`, Postman, or Python to send fake GroupMe webhooks.

### Method A: Using curl

Create a test script `test_webhook.sh`:

```bash
#!/bin/bash

# Test 1: No crew tonight
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "attachments": [],
    "avatar_url": "https://i.groupme.com/123456789",
    "created_at": 1732334400,
    "group_id": "12345678",
    "id": "173233440012345678",
    "name": "George Nowakowski",
    "sender_id": "12345",
    "sender_type": "user",
    "system": false,
    "text": "43 does not have a crew tonight from 1800 to midnight",
    "user_id": "12345"
  }'

echo "\n\n"

# Test 2: No crew Saturday morning
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "attachments": [],
    "avatar_url": "https://i.groupme.com/123456789",
    "created_at": 1732334400,
    "group_id": "12345678",
    "id": "173233440012345679",
    "name": "Katie Sowden",
    "sender_id": "12346",
    "sender_type": "user",
    "system": false,
    "text": "35 does not have a crew for Saturday morning",
    "user_id": "12346"
  }'

echo "\n"
```

Run it:
```bash
chmod +x test_webhook.sh
./test_webhook.sh
```

### Method B: Using Python

Create `test_bot.py`:

```python
#!/usr/bin/env python3
"""Test script to send mock GroupMe webhooks to the bot."""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

# Sample test messages
TEST_MESSAGES = [
    {
        "sender": "George Nowakowski",
        "text": "43 does not have a crew tonight from 1800 to midnight",
        "description": "No crew tonight - partial shift"
    },
    {
        "sender": "Katie Sowden",
        "text": "35 does not have a crew for Saturday morning",
        "description": "No crew Saturday morning"
    },
    {
        "sender": "Mike B",
        "text": "54 is fully staffed tonight",
        "description": "Crew available"
    },
    {
        "sender": "George Nowakowski",
        "text": "Hey everyone, just checking in!",
        "description": "Non-shift message (should be ignored)"
    },
    {
        "sender": "Unknown Person",
        "text": "42 has no crew tonight",
        "description": "Unauthorized sender (should be ignored)"
    }
]

def create_webhook_payload(sender_name, text):
    """Create a mock GroupMe webhook payload."""
    return {
        "attachments": [],
        "avatar_url": "https://i.groupme.com/123456789",
        "created_at": int(time.time()),
        "group_id": "12345678",
        "id": f"{int(time.time() * 1000)}",
        "name": sender_name,
        "sender_id": str(hash(sender_name) % 100000),
        "sender_type": "user",
        "system": False,
        "text": text,
        "user_id": str(hash(sender_name) % 100000)
    }

def test_webhook(sender, text, description):
    """Send a test webhook to the bot."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"Sender: {sender}")
    print(f"Message: {text}")
    print(f"{'='*80}")

    payload = create_webhook_payload(sender, text)

    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=payload,
            timeout=30
        )

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def main():
    """Run all tests."""
    print("Starting bot tests...")
    print(f"Target: {BASE_URL}")

    # Check if bot is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Bot is running (status: {response.json()['status']})\n")
    except requests.exceptions.RequestException:
        print("✗ Bot is not running! Start it with: python run.py")
        return

    # Run tests
    for test in TEST_MESSAGES:
        test_webhook(test["sender"], test["text"], test["description"])
        time.sleep(2)  # Wait between tests

    print(f"\n{'='*80}")
    print("All tests completed!")
    print(f"Check logs/chatbot.log for detailed processing logs")
    print(f"Check logs/message_log_{datetime.now().strftime('%Y%m%d')}.jsonl for message details")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
```

Run it:
```bash
chmod +x test_bot.py
python test_bot.py
```

### Method C: Using Postman

1. Open Postman
2. Create a new POST request
3. URL: `http://localhost:8080/webhook`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
```json
{
  "attachments": [],
  "avatar_url": "https://i.groupme.com/123456789",
  "created_at": 1732334400,
  "group_id": "12345678",
  "id": "173233440012345678",
  "name": "George Nowakowski",
  "sender_id": "12345",
  "sender_type": "user",
  "system": false,
  "text": "43 does not have a crew tonight from 1800 to midnight",
  "user_id": "12345"
}
```

### What to Watch

When testing locally, monitor:

1. **Terminal output** - Real-time processing logs
2. **logs/chatbot.log** - Detailed application logs
3. **logs/message_log_YYYYMMDD.jsonl** - Full message processing details

---

## Option 3: Unit Testing

Run the automated test suite:

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_roster.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=src/station95chatbot --cov-report=html
```

---

## Option 4: Testing Agentic AI Workflow

The agentic AI workflow is more complex and requires additional setup. This section shows you how to test it locally.

### What is Agentic Mode?

Agentic mode uses LangGraph to orchestrate multi-step workflows where the AI:
- Calls tools to check the schedule
- Validates changes before executing
- Sends warnings to GroupMe
- Handles complex multi-command messages

See [AGENTIC_AI_GUIDE.md](AGENTIC_AI_GUIDE.md) for full details.

### Prerequisites

1. **Install Dependencies**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set AI Mode in .env**
   ```bash
   # Add or update in .env file
   AI_MODE=agentic

   # Choose your AI provider
   AI_PROVIDER=openai  # or 'anthropic'
   OPENAI_API_KEY=sk-...
   ```

3. **Configure Calendar Service**

   The agentic workflow needs a calendar service that supports **both commands AND schedule queries**. You have two options:

   **Option A: Use Mock Calendar Server** (Recommended for testing)
   ```bash
   # See "Setting Up Mock Calendar Server" section below
   CALENDAR_SERVICE_URL=http://localhost:9999
   ```

   **Option B: Use Real Calendar Service** (If it supports getSchedule)
   ```bash
   CALENDAR_SERVICE_URL=https://your-calendar-api.com/v1
   ```

### Quick Test: Run the Test Suite

The easiest way to test the agentic workflow:

```bash
# Make sure you're in the project root
cd /path/to/station95chatbot

# Activate virtual environment
source venv/bin/activate

# Set agentic mode (if not in .env)
export AI_MODE=agentic

# Run the test suite
python test_agentic.py
```

**What this tests:**
1. Simple single-command message
2. Complex multi-command message
3. Message requiring schedule validation
4. Non-shift message filtering

**Expected output:**
```
╔════════════════════════════════════════════════════════════════════════╗
║           AGENTIC AI WORKFLOW TEST SUITE                              ║
║           Station 95 Chatbot - LangGraph Implementation               ║
╚════════════════════════════════════════════════════════════════════════╝

================================================================================
TEST 1: Simple Message
================================================================================

Message: Squad 34 will not have a crew tonight
Timestamp: 1733334400

🤖 Node: Interpret Message
🔍 Tool: get_schedule(20251204, 20251204, squad=34)
✅ Schedule fetched successfully
✅ Parsed 1 requests

🔍 Node: Validate Changes
Validation PASSED

⚡ Node: Execute Commands
✅ Executed: noCrew for Squad 34

--- RESULT ---
Is shift request: True
Confidence: 95%
Parsed requests: 1
  1. noCrew - Squad 34 - 20251204 1800-0600
Warnings: []
Critical warnings: []
Execution results: 1 command(s)

...
```

### Test with Real Webhooks

To test the agentic workflow with actual GroupMe webhooks:

#### 1. Start Mock Calendar Server

```bash
# Terminal 1: Start mock calendar server
python mock_calendar_enhanced.py
```

See [Setting Up Mock Calendar Server](#setting-up-mock-calendar-server) section below for the enhanced mock server code.

#### 2. Start the Bot

```bash
# Terminal 2: Start the bot in agentic mode
export AI_MODE=agentic
python run.py
```

#### 3. Send Test Messages

**Option A: Using curl**

```bash
# Terminal 3: Send test messages
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "name": "George Nowakowski",
    "text": "42 will not have a crew tonight midnight - 6 or Thursday midnight - 6. We will add a crew for Saturday morning shift",
    "created_at": '$(date +%s)',
    "group_id": "12345678",
    "id": "test-'$(date +%s)'",
    "sender_id": "12345",
    "sender_type": "user",
    "system": false,
    "user_id": "12345",
    "attachments": []
  }'
```

**Option B: Using the test script**

```bash
python test_bot_agentic.py
```

Create `test_bot_agentic.py`:

```python
#!/usr/bin/env python3
"""Test script for agentic AI workflow with mock webhooks."""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

# Complex test messages for agentic mode
TEST_MESSAGES = [
    {
        "sender": "George Nowakowski",
        "text": "42 will not have a crew tonight midnight - 6 or Thursday midnight - 6",
        "description": "Multiple noCrew commands"
    },
    {
        "sender": "Katie Sowden",
        "text": "35 out tonight and tomorrow morning",
        "description": "Two different shifts"
    },
    {
        "sender": "Mike B",
        "text": "Remove Squad 42 from tonight's evening shift",
        "description": "Should check if station goes out of service"
    },
    {
        "sender": "George Nowakowski",
        "text": "43 does not have a crew tonight. Add 43 for Saturday morning instead",
        "description": "Remove one, add another"
    }
]

def create_webhook_payload(sender_name, text):
    """Create a mock GroupMe webhook payload."""
    return {
        "attachments": [],
        "avatar_url": "https://i.groupme.com/123456789",
        "created_at": int(time.time()),
        "group_id": "12345678",
        "id": f"{int(time.time() * 1000)}",
        "name": sender_name,
        "sender_id": str(hash(sender_name) % 100000),
        "sender_type": "user",
        "system": False,
        "text": text,
        "user_id": str(hash(sender_name) % 100000)
    }

def test_webhook(sender, text, description):
    """Send a test webhook to the bot."""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {description}")
    print(f"👤 Sender: {sender}")
    print(f"💬 Message: {text}")
    print(f"{'='*80}")

    payload = create_webhook_payload(sender, text)

    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=payload,
            timeout=60  # Agentic mode can take longer
        )

        print(f"\n✅ Status Code: {response.status_code}")

        result = response.json()
        print(f"\n📊 RESULTS:")
        print(f"  Processed: {result.get('processed', False)}")
        print(f"  Commands sent: {result.get('command_sent', False)}")

        if 'interpretation' in result:
            interp = result['interpretation']
            print(f"  Is shift request: {interp.get('is_shift_request', False)}")
            print(f"  Confidence: {interp.get('confidence', 0)}%")

            if 'parsed_requests' in interp:
                print(f"  Parsed requests: {len(interp['parsed_requests'])}")
                for i, req in enumerate(interp['parsed_requests'], 1):
                    print(f"    {i}. {req.get('action')} - Squad {req.get('squad')} - {req.get('date')}")

            if interp.get('warnings'):
                print(f"\n  ⚠️  Warnings:")
                for w in interp['warnings']:
                    print(f"    - {w}")

            if interp.get('critical_warnings'):
                print(f"\n  🚨 Critical Warnings:")
                for w in interp['critical_warnings']:
                    print(f"    - {w}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🚀 AGENTIC AI WORKFLOW - LOCAL TESTING")
    print("="*80 + "\n")

    # Check if bot is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Bot is running (status: {response.json()['status']})")
        print(f"✓ Make sure AI_MODE=agentic is set\n")
    except requests.exceptions.RequestException:
        print("✗ Bot is not running! Start it with: python run.py")
        print("✗ Make sure AI_MODE=agentic in .env\n")
        return

    # Run tests
    for test in TEST_MESSAGES:
        test_webhook(test["sender"], test["text"], test["description"])
        print("\n⏳ Waiting 3 seconds before next test...\n")
        time.sleep(3)

    print("="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
    print("\n📝 Check logs for detailed workflow execution:")
    print(f"   - logs/chatbot.log")
    print(f"   - logs/message_log_{datetime.now().strftime('%Y%m%d')}.jsonl\n")

if __name__ == "__main__":
    main()
```

Run it:
```bash
chmod +x test_bot_agentic.py
python test_bot_agentic.py
```

### What to Watch For

When testing agentic mode, monitor your terminals:

**Terminal 1 (Mock Calendar Server):**
```
📅 GET /v1?action=getSchedule&start_date=20251204&end_date=20251204
✅ Returning mock schedule with 3 squads
```

**Terminal 2 (Bot - Agentic Workflow):**
```
INFO: Processing message from George Nowakowski
INFO: Using AGENTIC processing for message
🤖 Node: Interpret Message
🔍 Tool: get_schedule(20251204, 20251204, squad=42)
✅ Schedule fetched successfully
🔍 Tool: count_active_crews(date=20251204, shift_start=1800, shift_end=0600, excluding=42)
✅ Count: 2 active crews
✅ Parsed 2 requests
🔍 Node: Validate Changes
Validation PASSED
⚡ Node: Execute Commands (2 commands)
✅ Executed: noCrew for Squad 42
✅ Executed: noCrew for Squad 42
✅ Workflow complete
```

### Debugging Agentic Workflow

**Enable verbose logging:**
```bash
# In .env
LOG_LEVEL=DEBUG
```

**Check LangGraph execution:**
```python
# The workflow state is logged at each node
# Look for these in logs:
# - 🤖 Node: Interpret Message
# - 🔍 Node: Validate Changes
# - ⚠️  Node: Send Warnings
# - ⚡ Node: Execute Commands
```

**Common issues:**

1. **Tools not being called**
   - Check API key is valid
   - Verify AI_MODE=agentic
   - Check logs for LLM errors

2. **Calendar API errors**
   - Verify mock calendar server is running
   - Check CALENDAR_SERVICE_URL in .env
   - Ensure getSchedule endpoint exists

3. **Warnings not sent**
   - Check GROUPME_BOT_ID is set
   - Verify GroupMe API connectivity
   - Test GroupMeClient directly

---

## Setting Up Mock Calendar Server

The agentic workflow needs a calendar server that supports **both** commands and schedule queries. Here's an enhanced mock server:

### Create `mock_calendar_enhanced.py`

```python
#!/usr/bin/env python3
"""
Enhanced mock calendar server for testing agentic AI workflow.

This mock server supports:
- GET /v1?action=getSchedule - Return mock schedule
- GET /v1?action=noCrew/addShift/obliterateShift - Execute commands
"""

from fastapi import FastAPI, Query
from typing import Literal
import uvicorn
from datetime import datetime, timedelta
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
            "getSchedule": "GET /?action=getSchedule&start_date=YYYYMMDD&end_date=YYYYMMDD&squad=XX",
            "noCrew": "GET /?action=noCrew&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "addShift": "GET /?action=addShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX",
            "obliterateShift": "GET /?action=obliterateShift&date=YYYYMMDD&shift_start=HHMM&shift_end=HHMM&squad=XX"
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
```

### Start the Mock Calendar Server

```bash
# Make executable
chmod +x mock_calendar_enhanced.py

# Run it
python mock_calendar_enhanced.py
```

**Expected output:**
```
================================================================================
🚀 STARTING ENHANCED MOCK CALENDAR SERVER
================================================================================

This server supports:
  ✓ getSchedule - Return mock schedule data
  ✓ noCrew - Mark crew as unavailable
  ✓ addShift - Add new shift
  ✓ obliterateShift - Remove shift

================================================================================
Running on: http://localhost:9999
Set in .env: CALENDAR_SERVICE_URL=http://localhost:9999/v1
================================================================================

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:9999
```

### Test the Mock Calendar Server

```bash
# Get schedule
curl "http://localhost:9999/v1?action=getSchedule&start_date=20251204&end_date=20251210"

# Execute command
curl "http://localhost:9999/v1?action=noCrew&date=20251204&shift_start=1800&shift_end=0600&squad=42"
```

### Update .env to Use Mock Server

```bash
# In your .env file
CALENDAR_SERVICE_URL=http://localhost:9999/v1
```

Now when you run the agentic workflow, it will use this mock server instead of the real calendar API!

---

## Debugging Tips

### View Real-Time Logs

```bash
# Follow all logs
tail -f logs/chatbot.log

# Follow error logs only
tail -f logs/errors.log

# Follow message processing logs
tail -f logs/message_log_$(date +%Y%m%d).jsonl | jq .
```

### Check Bot Health

```bash
# Health check
curl http://localhost:8080/health

# Basic status
curl http://localhost:8080/
```

### Test AI Integration Directly

Create `test_ai.py`:

```python
from src.station95chatbot.ai_processor import AIProcessor
from src.station95chatbot.config import settings
import time

# Initialize AI processor
ai = AIProcessor()

# Test interpretation
result = ai.interpret_message(
    sender_name="George Nowakowski",
    sender_squad=43,
    sender_role="Chief",
    message_text="43 does not have a crew tonight from 1800 to midnight",
    message_timestamp=int(time.time())
)

print(f"Is shift request: {result.is_shift_request}")
print(f"Action: {result.action}")
print(f"Squad: {result.squad}")
print(f"Date: {result.date}")
print(f"Time: {result.shift_start} - {result.shift_end}")
print(f"Confidence: {result.confidence}%")
print(f"Reasoning: {result.reasoning}")
```

### Bypass Calendar Service

To test without hitting the real calendar service, temporarily modify `.env`:

```bash
# Point to a mock endpoint or disable
CALENDAR_SERVICE_URL=http://localhost:9999/mock-commands
```

Or create a simple mock server:

```python
# mock_calendar.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/mock-commands")
async def mock_calendar(action: str, date: str, shift_start: str, shift_end: str, squad: int):
    print(f"📅 Mock calendar received: {action} for squad {squad} on {date} ({shift_start}-{shift_end})")
    return {"status": "success", "message": "Mock calendar updated"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
```

Run in separate terminal:
```bash
python mock_calendar.py
```

---

## Recommended Testing Workflow

### For Development

1. **Start with Unit Tests** - Verify core logic
   ```bash
   pytest tests/ -v
   ```

2. **Test with Mock Webhooks** - Test full pipeline without GroupMe
   ```bash
   python test_bot.py
   ```

3. **Test with ngrok + Test GroupMe** - End-to-end testing
   ```bash
   # Terminal 1: Start bot
   python run.py

   # Terminal 2: Start ngrok
   ngrok http 8080

   # Update GroupMe webhook URL
   # Send test messages in test group
   ```

### For Production Deployment

1. Use ngrok (or similar) initially to test webhook integration
2. Once verified, deploy to a server with a static IP/domain
3. Update GroupMe webhook to point to production server
4. Monitor logs carefully for the first few days

---

## Troubleshooting

### Bot not receiving webhooks via ngrok

1. ✓ Check ngrok is running: `curl https://YOUR-NGROK-URL.ngrok.io/health`
2. ✓ Check GroupMe webhook URL matches ngrok URL
3. ✓ Check ngrok web interface at http://127.0.0.1:4040
4. ✓ Verify bot is running on port 8080

### Mock webhooks not working

1. ✓ Check bot is running: `curl http://localhost:8080/health`
2. ✓ Verify sender name matches roster exactly (case-sensitive)
3. ✓ Check logs for detailed error messages

### AI not interpreting correctly

1. ✓ Check API key is valid in `.env`
2. ✓ Review `logs/message_log_YYYYMMDD.jsonl` for AI reasoning
3. ✓ Adjust confidence threshold temporarily for testing
4. ✓ Test AI directly with `test_ai.py` script

---

## Summary

| Method | GroupMe Required | Internet Required | Best For |
|--------|-----------------|-------------------|----------|
| ngrok + Real GroupMe | ✓ Yes | ✓ Yes | End-to-end testing |
| Mock Webhooks | ✗ No | ✗ No | Fast iteration, debugging |
| Unit Tests | ✗ No | ✗ No | Core logic verification |

**Recommended:** Start with mock webhooks for development, then use ngrok for final testing before production deployment.
