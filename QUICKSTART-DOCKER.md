# Docker Quick Start Guide

Get the GroupMe poller running in Docker in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- GroupMe API credentials
- Roster file configured

## Step-by-Step Setup

### 1. Create Environment File

```bash
cp .env.docker.example .env
```

### 2. Edit `.env` with Your Credentials

```bash
nano .env
```

**Minimum required settings:**
```bash
GROUPME_API_TOKEN=your_groupme_token_here
GROUPME_GROUP_ID=your_group_id_here
GROUPME_BOT_ID=your_bot_id_here

AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here

CALENDAR_SERVICE_URL=https://your-calendar-api.com/v1
```

### 3. Verify Roster File Exists

```bash
ls -la data/roster.json
```

If it doesn't exist, create it:
```bash
cp data/roster.json.example data/roster.json
# Edit with your team members
```

### 4. Start the Container

```bash
docker-compose up -d
```

### 5. Verify It's Running

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f
```

You should see:
```
✓ Initial poll successful!
Starting cron scheduler...
Schedule: Every 10 minutes
Container is now running.
```

### 6. Monitor Activity

```bash
# Watch cron execution logs
docker-compose exec groupme-poller tail -f /app/logs/cron.log

# Watch application logs
docker-compose exec groupme-poller tail -f /app/logs/station95chatbot.log
```

## Common Commands

```bash
# Stop the poller
docker-compose down

# Restart the poller
docker-compose restart

# View recent logs
docker-compose logs --tail=50

# Run a manual poll (without waiting for cron)
docker-compose exec groupme-poller python -m src.station95chatbot.poll_messages

# Check state file
cat data/last_message_id.txt

# Reset state (reprocess messages)
rm data/last_message_id.txt
docker-compose restart
```

## Changing Poll Frequency

The default is every 10 minutes. To change:

1. Edit `docker/crontab`:
   ```bash
   # For every 5 minutes, change to:
   */5 * * * * cd /app && /usr/local/bin/python -m src.station95chatbot.poll_messages >> /app/logs/cron.log 2>&1
   ```

2. Rebuild and restart:
   ```bash
   docker-compose up -d --build
   ```

## Troubleshooting

### Container exits immediately

Check logs for errors:
```bash
docker-compose logs
```

Common issues:
- Missing environment variables
- Invalid API keys
- Roster file not found

### No messages being processed

1. Check cron is running:
   ```bash
   docker-compose exec groupme-poller pgrep cron
   ```

2. Test manual poll:
   ```bash
   docker-compose exec groupme-poller python -m src.station95chatbot.poll_messages
   ```

3. Check state file:
   ```bash
   cat data/last_message_id.txt
   ```

## Next Steps

See [DOCKER.md](DOCKER.md) for complete documentation including:
- Production deployment
- Security considerations
- Advanced configuration
- Monitoring and debugging
