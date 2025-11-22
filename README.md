# Station 95 GroupMe Chatbot

An intelligent bot that monitors a GroupMe chat for rescue squad shift change requests, interprets natural language messages using AI, and automatically updates the rescue squad calendar system.

## Features

- **Natural Language Processing**: Uses AI (OpenAI or Anthropic) to interpret colloquial shift change requests
- **Automatic Calendar Updates**: Sends structured commands to the calendar service
- **Smart Filtering**: Only processes messages from authorized roster members
- **Confidence Scoring**: Flags low-confidence interpretations for manual review
- **Comprehensive Logging**: Tracks all message processing for review and improvement
- **Retry Logic**: Automatically retries failed calendar service requests

## Project Structure

```
station95chatbot/
├── src/station95chatbot/
│   ├── __init__.py
│   ├── main.py                 # Main entry point
│   ├── config.py               # Configuration management
│   ├── models.py               # Pydantic data models
│   ├── roster.py               # Roster management
│   ├── ai_processor.py         # AI/LLM integration
│   ├── calendar_client.py      # Calendar service client
│   ├── message_processor.py    # Message processing pipeline
│   ├── webhook_handler.py      # GroupMe webhook handler
│   └── logging_config.py       # Logging setup
├── data/
│   └── roster.json             # Squad member roster
├── logs/                       # Application logs
├── tests/                      # Unit tests
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project configuration
├── .env.example               # Environment variables template
├── run.py                     # Convenience runner script
└── README.md                  # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- GroupMe account with bot created
- OpenAI API key OR Anthropic API key
- Access to the 95CalendarAdmin service

### Setup Steps

1. **Clone the repository**:
   ```bash
   cd /path/to/station95chatbot
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your credentials:
   ```
   GROUPME_BOT_ID=your_bot_id_here
   GROUPME_API_TOKEN=your_api_token_here
   GROUPME_GROUP_ID=your_group_id_here

   # Choose OpenAI or Anthropic
   AI_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here

   CALENDAR_SERVICE_URL=http://localhost:8000/commands
   WEBHOOK_PORT=8080
   ```

5. **Update the roster** (if needed):
   Edit `data/roster.json` to match your squad member list.

## Running the Bot

### Development Mode

```bash
python run.py
```

Or using the module directly:
```bash
python -m src.station95chatbot.main
```

### Production Mode

For production deployment, consider using a process manager like `systemd`, `supervisor`, or `pm2`.

Example systemd service file (`/etc/systemd/system/station95chatbot.service`):

```ini
[Unit]
Description=Station 95 GroupMe Chatbot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/station95chatbot
Environment=PATH=/path/to/station95chatbot/venv/bin
ExecStart=/path/to/station95chatbot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## GroupMe Bot Setup

1. **Create a bot** at https://dev.groupme.com/bots
2. **Configure webhook URL**: Set to `http://your-server:8080/webhook`
   - For development/testing, use a tool like [ngrok](https://ngrok.com/) to expose localhost:
     ```bash
     ngrok http 8080
     ```
3. **Copy the Bot ID** and add to your `.env` file

## Usage

Once running, the bot will:

1. Listen for messages in the configured GroupMe chat
2. Filter messages from roster members containing shift-related keywords
3. Send relevant messages to AI for interpretation
4. Execute calendar commands for high-confidence interpretations (>70%)
5. Log all processing activity for review

### Example Messages

The bot can interpret messages like:

- "42 does not have a crew tonight from 1800 - midnight"
- "Still no luck getting a crew until midnight. Fully staffed after"
- "54 does not have a crew for Saturday morning"
- "43 will not have a crew in the morning, but will have one in the afternoon"

### Calendar Commands

The bot sends HTTP POST requests to the calendar service with parameters:

- `action`: `noCrew`, `addShift`, or `obliterateShift`
- `date`: Date in YYYYMMDD format
- `shift_start`: Time in HHMM format
- `shift_end`: Time in HHMM format
- `squad`: Squad number (34, 35, 42, 43, 54)

Example:
```
http://localhost:8000/commands/?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42
```

## Monitoring and Logs

### Log Files

- `logs/chatbot.log` - All application logs
- `logs/errors.log` - Error logs only
- `logs/message_log_YYYYMMDD.jsonl` - Detailed message processing logs (JSONL format)

### Health Check

The bot exposes health check endpoints:

- `GET /` - Basic status
- `GET /health` - Health check

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key settings:

- `CONFIDENCE_THRESHOLD` - Minimum confidence score to execute commands (default: 70)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `AI_PROVIDER` - Choose `openai` or `anthropic`

### Roster Management

The roster is stored in `data/roster.json`. Update this file to add/remove squad members.

Format:
```json
{
  "members": [
    {
      "name": "Full Name",
      "title": "Chief" or "Member",
      "squad": 34,
      "groupme_name": "GroupMe Display Name"
    }
  ]
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
pip install black flake8
black src/
flake8 src/
```

## Troubleshooting

### Bot not receiving messages

1. Check webhook URL is correctly configured in GroupMe
2. Verify the bot is running and accessible
3. Check firewall settings allow incoming connections
4. Review logs for connection errors

### Low confidence interpretations

1. Review `logs/message_log_YYYYMMDD.jsonl` for interpretation details
2. Consider adjusting the AI prompt in `ai_processor.py`
3. Lower `CONFIDENCE_THRESHOLD` if too conservative (not recommended below 60)

### Calendar service errors

1. Verify `CALENDAR_SERVICE_URL` is correct
2. Check calendar service is running and accessible
3. Review calendar service logs for errors
4. Test with curl:
   ```bash
   curl -X POST "http://localhost:8000/commands/?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42"
   ```

## Future Enhancements

- Confirmation messages posted back to GroupMe
- Interactive clarification for low-confidence interpretations
- Calendar query capability
- Analytics dashboard
- Multi-language support

## License

Copyright (c) 2025 Station 95

## Support

For issues or questions, contact George Nowakowski or file an issue in the repository
