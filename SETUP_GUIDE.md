# Station 95 ChatBot - Setup Guide

Perfect! I've successfully created a complete Python application structure and implemented the GroupMe bot specification. Here's what has been built:

## Project Structure Created

```
station95chatbot/
├── src/station95chatbot/          # Main application code
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── config.py                  # Environment configuration
│   ├── models.py                  # Pydantic data models
│   ├── roster.py                  # Squad member management
│   ├── ai_processor.py            # AI/LLM integration (OpenAI/Anthropic)
│   ├── calendar_client.py         # Calendar service HTTP client
│   ├── message_processor.py       # Message processing pipeline
│   ├── webhook_handler.py         # FastAPI webhook server
│   └── logging_config.py          # Logging setup
├── data/
│   └── roster.json                # Squad roster with all members
├── tests/                         # Unit tests
│   ├── __init__.py
│   ├── test_roster.py
│   └── test_models.py
├── logs/                          # Auto-generated logs directory
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
├── run.py                         # Convenience runner
└── README.md                      # Complete documentation
```

## Key Features Implemented

1. **GroupMe Webhook Handler** - FastAPI server that receives and processes GroupMe messages
2. **AI Integration** - Supports both OpenAI (GPT-4) and Anthropic (Claude) for natural language interpretation
3. **Smart Message Processing** - Filters messages, validates senders, and interprets shift changes
4. **Calendar Service Client** - HTTP client with retry logic to send commands to calendar service
5. **Roster Management** - Squad member database with authorization checking
6. **Comprehensive Logging** - Multiple log levels and detailed message tracking
7. **Confidence Scoring** - Only executes commands above 70% confidence threshold
8. **Test Suite** - Unit tests for core functionality

## Next Steps to Run the Bot

1. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the bot**:
   ```bash
   python run.py
   ```

4. **Set up GroupMe webhook**:
   - Point your GroupMe bot webhook to `http://your-server:8080/webhook`
   - For local testing, use ngrok: `ngrok http 8080`

The bot will now listen for shift change messages, interpret them using AI, and automatically update the calendar system!
