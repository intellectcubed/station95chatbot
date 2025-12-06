# GroupMe Shift Management Bot - Technical Specification

## Project Overview

Create an intelligent bot that monitors a GroupMe chat for rescue squad shift change requests, interprets natural language messages using AI, and automatically updates the rescue squad calendar system.

## System Architecture

### Components

1. **GroupMe Bot Service** - Listens to GroupMe chat via webhook
2. **AI Processing Module** - Uses LLM (ChatGPT API) to interpret natural language requests
3. **Command Generator** - Translates AI interpretation into structured commands
4. **Calendar Service Interface** - Sends commands to existing 95CalendarAdmin application
5. **Logging & Monitoring** - Tracks bot activity and errors

### Data Flow

```
GroupMe Chat Message
    ↓
GroupMe Bot Webhook (receives message)
    ↓
Message Filter (squad chief messages + shift-related content)
    ↓
AI/LLM Processing (interpret natural language)
    ↓
Command Generator (create structured command)
    ↓
HTTP POST to calendar_service.py
    ↓
calendar_commands.py execution
    ↓
Calendar Updated
```

## Business Context

### Rescue Squad Operations

- **5 Rescue Squads**: 34, 35, 42, 43, 54
- **Shift Structure**:
  - Weekends: 12-hour shifts (0600-1800 or 1800-0600)
  - Weeknights: 12-hour shifts (0600-1800 or 1800-0600)
  - Morning shift: 0600-1800
  - Evening/Night shift: 1800-0600
- **Crew Configuration**: 
  - 1-3 crews per shift (typically 2)
  - Each shift has a supervisor called "Tango"

### Squad Leadership Roster

| Name | Title | Squad |
|------|-------|-------|
| Mike Halperin | Chief | 34 |
| Katie Sowden | Chief | 35 |
| Kholer | Chief | 42 |
| George Nowakowski | Chief | 43 |
| Mike B | Chief | 54 |
| Charles Sharkey | Member | 34 |
| Joe | Member | 34 |
| Steph L | Member | 34 |
| Stanley Stellakis | Member | 34 |
| Marc Sowden | Member | 35 |
| Javier M | Member | 42 |
| Jim R | Member | 43 |
| Lou DiGiovanni | Member | 43 |
| Alice Hadley | Member | 43 |
| Sara Rall | Member | 43 |
| Diane Chrinko | Member | 54 |
| Donna Rogers | Member | 54 |
| Freedie P | Member | 54 |
| Steve Weinman | Member | 54 |
| Jim Barry | Member | 54 |

## Natural Language Processing Requirements

### Sample Utterances

The bot must interpret various colloquial expressions of shift changes:

1. "42 does not have a crew tonight from 1800 - midnight"
2. "I had a call out for tonight's shift, there will be no crew"
3. "Still no luck in getting a crew until midnight. We are fully staffed after midnight"
4. "54 does not have a crew for Saturday morning"
5. "Still looking for one member to join the crew"
6. "Saturday, 43 will not have a crew in the morning, but will have one in the afternoon"

### Interpretation Rules

1. **Squad Identification**:
   - If squad number explicitly mentioned (e.g., "42", "Squad 43"), use that squad
   - If no squad mentioned, use the sender's squad (from roster lookup)
   - Exception: If sender explicitly mentions another squad, use mentioned squad
     - Example: George Nowakowski (Chief, 43) says "Confirming that 35 will not have a crew tonight" → Squad 35

2. **Time Interpretation**:
   - "tonight" = current date, evening shift (1800-0600 next day)
   - "today" = current date, infer shift from current time
   - "tomorrow" = next date, infer shift from context
   - "morning" = 0600-1800
   - "afternoon" = 1200-1800
   - "evening" = 1800-0600
   - "Saturday morning" = next Saturday, 0600-1800
   - Specific times override defaults (e.g., "1800 - midnight" = 1800-0000)

3. **Action Determination**:
   - "no crew", "does not have a crew", "won't have a crew" → `noCrew` action
   - "will have a crew", "fully staffed" → `addShift` action (if not already scheduled)
   - "cancel shift", "remove shift" → `obliterateShift` action
   - Partial crew mentions ("looking for one member") → May require confirmation or logging only

4. **Date Resolution**:
   - Must convert relative dates ("tonight", "Saturday") to absolute dates (YYYYMMDD format)
   - Consider current date/time when interpreting

## Command Specification

### Command Structure

All commands must be converted to HTTP POST requests with the following parameters:

**Endpoint**: `http://localhost:8000/commands`

**Parameters**:
- `action` (required): One of [`noCrew`, `addShift`, `obliterateShift`]
- `date` (required): Date in YYYYMMDD format
- `shift_start` (required): Time in HHMM format (e.g., "0600", "1800")
- `shift_end` (required): Time in HHMM format (e.g., "1800", "0600")
- `squad` (required): Squad number [34, 35, 42, 43, 54]

**Example URL**:
```
http://localhost:8000/commands/?action=noCrew&date=20251110&shift_start=1800&shift_end=0600&squad=42
```

### Action Definitions

1. **noCrew**: Remove a crew from a scheduled shift (crew cannot staff the shift)
2. **addShift**: Add a crew to a shift (crew is now available)
3. **obliterateShift**: Completely remove/cancel a shift from the calendar

## AI Processing Prompt Template

When sending messages to the AI/LLM for interpretation, use the following structured prompt:

```
You are a rescue squad shift management assistant. Analyze the following GroupMe message and extract shift change information.

**Message Details:**
- Sender: {sender_name}
- Sender's Squad: {sender_squad}
- Sender's Role: {sender_role}
- Message: "{message_text}"
- Timestamp: {message_timestamp}
- Current Date: {current_date}

**Your Task:**
Extract and return a JSON object with the following structure:

{
  "is_shift_request": boolean,
  "action": "noCrew" | "addShift" | "obliterateShift" | null,
  "squad": number (34, 35, 42, 43, or 54),
  "date": "YYYYMMDD",
  "shift_start": "HHMM",
  "shift_end": "HHMM",
  "confidence": number (0-100),
  "reasoning": "Brief explanation of interpretation"
}

**Rules:**
1. If squad not explicitly mentioned in message, use sender's squad: {sender_squad}
2. If sender mentions another squad explicitly, use that squad instead
3. Interpret colloquial time references:
   - "tonight" = today's evening shift (1800-0600)
   - "morning" = 0600-1800
   - "afternoon" = 1200-1800 (or use context)
   - "evening" = 1800-0600
4. Weekend shifts are 12 hours: 0600-1800 or 1800-0600
5. Weeknight shifts are 12 hours: 0600-1800 or 1800-0600
6. Return is_shift_request: false if message is not about shift changes
7. Only return confident interpretations (confidence > 70)

Respond ONLY with valid JSON. Do not include any explanation outside the JSON structure.
```

## Implementation Requirements

### GroupMe Bot Setup

1. **Bot Registration**:
   - Register bot with GroupMe API
   - Obtain bot ID and API token
   - Configure webhook URL to receive messages

2. **Webhook Handler**:
   - Create HTTP endpoint to receive GroupMe webhooks
   - Verify webhook authenticity
   - Filter out bot's own messages (avoid loops)

### Message Processing Pipeline

1. **Message Reception**:
   - Receive webhook from GroupMe
   - Extract: sender name, message text, timestamp, group ID

2. **Filtering**:
   - Check if sender is in roster
   - Determine if message likely contains shift information (keywords: crew, shift, squad, tonight, tomorrow, etc.)

3. **AI Processing**:
   - Send message + context to LLM API
   - Parse JSON response
   - Validate confidence threshold (>70%)

4. **Command Execution**:
   - Construct HTTP POST URL with parameters
   - Send request to calendar_service.py
   - Handle response and errors

5. **Logging**:
   - Log all interpretations (for review and improvement)
   - Log successful/failed command executions
   - Store ambiguous messages for manual review

### Error Handling

1. **Low Confidence**: If AI confidence < 70%, log message for manual review
2. **API Failures**: Retry logic for both GroupMe and Calendar Service
3. **Invalid Parameters**: Validate all parameters before sending to calendar service
4. **Ambiguous Messages**: Flag for human review, optionally post clarification request to GroupMe

### Security Considerations

1. **Authentication**: Verify GroupMe webhook signatures
2. **Authorization**: Only process messages from known roster members
3. **Rate Limiting**: Prevent spam or abuse
4. **Input Validation**: Sanitize all inputs before processing

## Testing Strategy

### Unit Tests
- Test date/time interpretation logic
- Test squad identification from roster
- Test command URL generation

### Integration Tests
- Mock GroupMe webhook payloads
- Mock AI/LLM responses
- Verify HTTP requests to calendar service

### Test Cases

| Input Message | Expected Output |
|---------------|-----------------|
| "42 does not have a crew tonight from 1800 - midnight" | action=noCrew, squad=42, shift_start=1800, shift_end=0000 |
| "Still no luck getting a crew until midnight. Fully staffed after" | Two commands: noCrew until midnight, addShift after midnight |
| "54 does not have a crew for Saturday morning" | action=noCrew, squad=54, next Saturday, shift_start=0600, shift_end=1800 |

## Deployment Considerations

1. **Environment Variables**:
   - GroupMe Bot ID
   - GroupMe API Token
   - Calendar Service URL
   - LLM API Key
   - Roster data file path

2. **Dependencies**:
   - Python 3.8+
   - requests library
   - OpenAI/Anthropic API client
   - Flask/FastAPI for webhook server

3. **Monitoring**:
   - Track message processing rate
   - Monitor AI API usage and costs
   - Alert on consecutive failures

## Future Enhancements

1. **Confirmation Messages**: Bot posts confirmation to GroupMe after executing command
2. **Interactive Clarification**: Bot asks for clarification when confidence is low
3. **Calendar Query**: Allow querying current shift status via GroupMe
4. **Analytics**: Track patterns in shift changes
5. **Multi-language Support**: Support additional languages if needed

## Success Metrics

- **Accuracy**: >90% correct interpretation of shift change requests
- **Response Time**: <5 seconds from message to command execution
- **Reliability**: 99%+ uptime for bot service
- **Manual Review Rate**: <10% of messages require human review

---

## Notes for AI Implementation

When implementing this bot, prioritize:
1. Robust natural language understanding with clear confidence scoring
2. Comprehensive logging for debugging and improvement
3. Graceful degradation (log for manual review when uncertain)
4. Clear error messages in logs
5. Idempotent command execution (safe to retry)

The bot should err on the side of caution - when in doubt about interpretation, log for manual review rather than executing potentially incorrect commands.
