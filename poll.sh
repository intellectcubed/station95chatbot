#!/bin/bash
# Wrapper script for polling GroupMe messages
# Can be called directly by cron or systemd timer

# Set script directory as working directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the polling script
python -m src.station95chatbot.poll_messages

# Capture exit code
EXIT_CODE=$?

# Exit with same code
exit $EXIT_CODE
