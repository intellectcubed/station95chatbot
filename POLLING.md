# GroupMe Message Polling

The chatbot supports two modes for receiving messages from GroupMe:

1. **Webhook Mode** (default): GroupMe pushes messages to your server in real-time
2. **Polling Mode**: Periodically fetch messages from GroupMe API

## When to Use Polling Mode

Use polling mode when:
- You can't expose a public webhook endpoint
- You're running behind a firewall or NAT
- You want more control over when messages are processed
- You're running in a restricted environment (e.g., local development)

## How Polling Works

The poller:
1. Fetches recent messages from GroupMe API
2. Tracks the last processed message ID in `data/last_message_id.txt`
3. Processes only new messages (messages newer than the last ID)
4. Updates the last message ID after processing
5. Reuses the same `MessageProcessor` as webhook mode

This ensures each message is processed exactly once, even if the poller runs multiple times.

## Setup

The poller requires the same configuration as webhook mode in your `.env` file:

```bash
# Required for polling
GROUPME_API_TOKEN=your_api_token_here
GROUPME_GROUP_ID=your_group_id_here

# Still needed for sending messages
GROUPME_BOT_ID=your_bot_id_here

# AI and other settings (same as webhook mode)
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
# ... etc
```

## Running the Poller

### Manual Execution

```bash
# Using the wrapper script (recommended)
./poll.sh

# Or directly with Python
python -m src.station95chatbot.poll_messages
```

### Automated Polling with Cron

To poll every 2 minutes, add this to your crontab (`crontab -e`):

```bash
*/2 * * * * cd /path/to/station95chatbot && ./poll.sh >> logs/poll.log 2>&1
```

More cron examples:
```bash
# Every 1 minute (more responsive, higher API usage)
* * * * * cd /path/to/station95chatbot && ./poll.sh >> logs/poll.log 2>&1

# Every 5 minutes (less API usage)
*/5 * * * * cd /path/to/station95chatbot && ./poll.sh >> logs/poll.log 2>&1

# Every 10 minutes during business hours (6am-6pm)
*/10 6-18 * * * cd /path/to/station95chatbot && ./poll.sh >> logs/poll.log 2>&1
```

### Automated Polling with Systemd Timer

Create `/etc/systemd/system/groupme-poll.service`:

```ini
[Unit]
Description=GroupMe Message Poller
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/station95chatbot
ExecStart=/path/to/station95chatbot/poll.sh
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/groupme-poll.timer`:

```ini
[Unit]
Description=Poll GroupMe every 2 minutes
Requires=groupme-poll.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=2min
Unit=groupme-poll.service

[Install]
WantedBy=timers.target
```

Enable and start the timer:

```bash
sudo systemctl enable groupme-poll.timer
sudo systemctl start groupme-poll.timer

# Check status
sudo systemctl status groupme-poll.timer
sudo systemctl list-timers
```

### AWS Lambda with EventBridge

Deploy the poller as a Lambda function and trigger it with EventBridge:

1. Package the application with dependencies
2. Deploy as Lambda function
3. Configure EventBridge rule with schedule expression:
   - `rate(2 minutes)` - Every 2 minutes
   - `rate(5 minutes)` - Every 5 minutes
   - `cron(0/2 * * * ? *)` - Cron format (every 2 minutes)

Lambda handler example:

```python
from station95chatbot.poll_messages import main

def lambda_handler(event, context):
    """Lambda handler for polling."""
    try:
        main()
        return {
            "statusCode": 200,
            "body": "Poll completed successfully"
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Poll failed: {str(e)}"
        }
```

## State Management

The poller stores the last processed message ID in `data/last_message_id.txt`. This file:
- Is created automatically on first run
- Is updated after each poll
- Should **not** be committed to git (already in `.gitignore`)
- Can be deleted to reset and reprocess messages

### Resetting State

To reprocess messages or start fresh:

```bash
# Delete the state file
rm data/last_message_id.txt

# Next poll will process recent messages as new
./poll.sh
```

Or use the Python API:

```python
from station95chatbot.groupme_poller import GroupMePoller
from station95chatbot.message_processor import MessageProcessor
# ... initialize components ...

poller = GroupMePoller(message_processor)
poller.reset_state()
```

## Monitoring

Check poll logs to monitor activity:

```bash
# View recent poll activity
tail -f logs/poll.log

# View application logs
tail -f logs/station95chatbot.log

# Check for errors
grep ERROR logs/station95chatbot.log
```

## API Rate Limits

GroupMe API rate limits:
- Standard tier: ~100 requests per minute
- Polling every 2 minutes = ~30 requests per hour (safe)
- Each poll fetches up to 20 messages by default

If you hit rate limits, increase polling interval or reduce the message fetch limit.

## Comparison: Polling vs Webhook

| Feature | Webhook Mode | Polling Mode |
|---------|-------------|--------------|
| Real-time | Yes (instant) | No (delayed by poll interval) |
| Network requirements | Public endpoint required | Outbound only |
| Resource usage | Event-driven (efficient) | Periodic (uses resources even when idle) |
| Reliability | Depends on network/server | Controlled by scheduler |
| Setup complexity | Higher (need public URL, port) | Lower (just schedule a script) |
| API usage | None (GroupMe pushes) | Moderate (fetch on each poll) |
| Best for | Production deployments | Development, restricted networks |

## Troubleshooting

### Messages not being processed

1. Check that `GROUPME_API_TOKEN` and `GROUPME_GROUP_ID` are set correctly
2. Verify the state file location exists (`data/` directory)
3. Check logs for API errors or authentication failures
4. Ensure roster members are configured correctly

### Duplicate processing

If messages are processed multiple times:
1. Check that only one poller instance is running
2. Verify state file is being written correctly
3. Check file permissions on `data/last_message_id.txt`

### Missing messages

If messages are being skipped:
1. Increase the `limit` parameter in `poller.poll(limit=20)`
2. Reduce polling interval to catch messages faster
3. Check for errors in message parsing or processing
