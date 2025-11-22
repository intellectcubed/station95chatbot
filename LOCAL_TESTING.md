# Local Testing Guide

This guide explains how to test the Station 95 ChatBot locally using different approaches.

## Table of Contents

1. [Option 1: Live Testing with ngrok + GroupMe](#option-1-live-testing-with-ngrok--groupme)
2. [Option 2: Simulated Testing (No GroupMe)](#option-2-simulated-testing-no-groupme)
3. [Option 3: Unit Testing](#option-3-unit-testing)
4. [Debugging Tips](#debugging-tips)

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
