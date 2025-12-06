# Agentic AI Implementation Guide

## Overview

This chatbot now supports two AI processing modes:

1. **Simple Mode** (default): Single LLM call to interpret and extract one command
2. **Agentic Mode**: Multi-step workflow with tools, validation, and complex reasoning

## What is Agentic AI?

**Agentic AI** refers to AI systems that can:
- **Use tools**: Call functions to gather information (check schedules, count crews, etc.)
- **Multi-step reasoning**: Break down complex requests into multiple actions
- **Make decisions**: Analyze state and decide what actions to take
- **Autonomous execution**: Complete tasks without human intervention at each step

### Example Comparison

**Simple Mode:**
```
User: "Squad 34 will not have a crew tonight"
System: [Single LLM call] → Execute noCrew command
```

**Agentic Mode:**
```
User: "42 will not have a crew tonight midnight - 6 or Thursday midnight - 6.
       We will add a crew for Saturday morning shift"

System:
  1. Parse message → Identify 3 requests
  2. Check schedule for tonight → Verify squad 42 is scheduled
  3. Check schedule for Thursday → Verify squad 42 is scheduled
  4. Count active crews after removing 42 → Check if station would be out of service
  5. Generate warnings if needed → Send to group chat
  6. Execute commands: noCrew (tonight), noCrew (Thursday), addShift (Saturday)
```

## Architecture

### Components

1. **tools.py**: LangChain tools that the AI can use
   - `get_schedule()`: Fetch current schedule
   - `check_squad_scheduled()`: Verify if a squad is scheduled
   - `count_active_crews()`: Count how many crews are on duty
   - `parse_time_reference()`: Parse natural language dates/times

2. **agentic_processor.py**: LangGraph workflow orchestrator
   - **Nodes**: Individual processing steps
     - `interpret_message_node`: LLM analyzes message with tools
     - `validate_changes_node`: Additional validation logic
     - `send_warnings_node`: Send warnings to GroupMe
     - `execute_commands_node`: Execute calendar commands
   - **Edges**: Define flow between nodes
     - Conditional routing based on state
     - Automatic loop execution until completion

3. **groupme_client.py**: Send messages back to the group chat
   - `send_message()`: Send regular messages
   - `send_warning()`: Send formatted warnings
   - `send_critical_alert()`: Send critical alerts

4. **calendar_client.py**: Enhanced with `get_schedule()` method
   - Fetch current schedule data
   - Used by tools to check state before executing commands

### Workflow Diagram

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│  interpret_message_node                     │
│  • LLM analyzes message                     │
│  • Makes tool calls in a loop               │
│  • Extracts parsed_requests, warnings       │
└──────┬──────────────────────────────────────┘
       │
       ▼
    [is_shift_request?]
       │
    Yes│                      No
       ▼                       ▼
┌────────────────┐         ┌──────┐
│  validate      │         │ END  │
│  • Check logic │         └──────┘
└─────┬──────────┘
      │
      ▼
   [has warnings?]
      │
   Yes│                   No
      ▼                    ▼
┌────────────┐      ┌────────────┐
│send_warnings│      │  execute   │
└─────┬──────┘      └─────┬──────┘
      │                   │
      └─────────┬─────────┘
                ▼
         ┌────────────┐
         │  execute   │
         │  commands  │
         └─────┬──────┘
               │
               ▼
            ┌──────┐
            │ END  │
            └──────┘
```

## Configuration

### Enable Agentic Mode

Set in your `.env` file:

```bash
AI_MODE=agentic  # or 'simple' for single LLM call
```

### Required API Keys

Agentic mode works with both providers:

**OpenAI (Recommended):**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Anthropic:**
```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage Examples

### Simple Request (Works in both modes)

```
Message: "Squad 34 will not have a crew tonight"

Result:
  • Action: noCrew
  • Squad: 34
  • Date: 20251204
  • Shift: 1800-0600
```

### Complex Request (Requires Agentic Mode)

```
Message: "42 will not have a crew tonight midnight - 6 or Thursday midnight - 6.
         We will add a crew for Saturday morning shift"

Agentic Workflow:
  1. Parse message → 3 requests identified
  2. Check schedule:
     - Tonight 0000-0600: Squad 42 scheduled?
     - Thursday 0000-0600: Squad 42 scheduled?
     - Saturday 0600-1800: Any conflicts?
  3. Validate:
     - Count crews after removing 42 tonight → 2 crews remaining ✓
     - Count crews after removing 42 Thursday → 1 crew remaining ✓
  4. Execute:
     - noCrew (tonight 0000-0600)
     - noCrew (Thursday 0000-0600)
     - addShift (Saturday 0600-1800)

Result:
  • 3 commands executed
  • No critical warnings (station remains in service)
```

### Request with Warning

```
Message: "Remove Squad 42 from tonight's evening shift"

Agentic Workflow:
  1. Check schedule for tonight 1800-0600
  2. Verify Squad 42 is scheduled ✓
  3. Count crews after removing Squad 42 → 0 crews!
  4. Generate CRITICAL WARNING:
     "🚨 Removing Squad 42 will leave Station 95 OUT OF SERVICE"
  5. Send warning to group chat
  6. Execute command anyway (with warning sent)

Result:
  • 1 command executed
  • 1 critical warning sent to group
```

## Testing

### Run Test Suite

```bash
cd /path/to/station95chatbot
source venv/bin/activate
python test_agentic.py
```

This will run 4 test scenarios:
1. Simple single-command message
2. Complex multi-command message
3. Message requiring schedule validation
4. Non-shift message (should be filtered)

### Manual Testing

```python
from station95chatbot.agentic_processor import AgenticProcessor
from datetime import datetime

processor = AgenticProcessor()

result = processor.process_message(
    message_text="42 will not have a crew tonight",
    sender_name="Test Chief",
    sender_squad=42,
    sender_role="Chief",
    message_timestamp=int(datetime.now().timestamp())
)

print(result)
```

## Key Benefits of Agentic Mode

1. **Multi-command parsing**: Handle complex messages with multiple requests
2. **State validation**: Check schedule before executing to prevent conflicts
3. **Safety checks**: Warn if changes would leave station out of service
4. **Schedule verification**: Confirm expectations match reality
5. **Automatic warnings**: Send alerts to group chat for issues
6. **Better reasoning**: LLM can use tools to make informed decisions

## Cost Considerations

Agentic mode uses more LLM tokens because:
- Multiple tool calls per message
- Longer context (tools, schedule data)
- Typically uses GPT-4o or Claude Sonnet (smarter models)

**Estimated costs per message:**
- Simple mode: $0.001 - $0.002 (GPT-4o-mini)
- Agentic mode: $0.01 - $0.05 (GPT-4o with tools)

For a rescue squad with ~50 shift messages/month:
- Simple mode: ~$0.10/month
- Agentic mode: ~$2.50/month

## When to Use Each Mode

### Use **Simple Mode** when:
- Messages are straightforward single requests
- Budget is very limited
- Calendar state checking is not required
- Fast response time is critical

### Use **Agentic Mode** when:
- Messages often contain multiple requests
- Need to validate against current schedule
- Want automatic warnings for conflicts
- Safety checks are important (out of service warnings)
- Users expect smart reasoning about complex scenarios

## Troubleshooting

### Issue: Agentic mode not activating

**Check:**
```bash
# Verify AI_MODE is set
echo $AI_MODE

# Should output: agentic
```

**Fix:**
```bash
# Add to .env file
AI_MODE=agentic

# Restart the application
```

### Issue: Tool calls failing

**Check logs:**
```
grep "Tool:" logs/station95chatbot.log
```

**Common causes:**
- Calendar service URL incorrect
- Network issues accessing calendar API
- Calendar API doesn't support getSchedule action

**Fix:**
Ensure your calendar service has a `getSchedule` endpoint:
```python
# In your calendar service
if action == "getSchedule":
    # Return schedule data
    return {
        "dates": [
            {
                "date": "20251204",
                "shifts": [
                    {"squad": 42, "shift_start": "1800", "shift_end": "0600", "crew_status": "available"},
                    ...
                ]
            }
        ]
    }
```

### Issue: Warnings not being sent

**Check:**
- `GROUPME_BOT_ID` is set correctly
- GroupMe API is accessible
- Bot has permission to post to the group

**Test manually:**
```python
from station95chatbot.groupme_client import GroupMeClient

client = GroupMeClient()
client.send_message("Test message")
```

## Advanced: Custom Tools

You can add your own tools to extend the agentic capabilities:

```python
# In tools.py

@tool
def check_member_availability(
    member_name: Annotated[str, "Name of the member"],
    date: Annotated[str, "Date in YYYYMMDD format"]
) -> bool:
    """
    Check if a specific member is available on a given date.

    This could check an availability calendar, vacation schedule, etc.
    """
    # Your implementation here
    return True

# Add to all_tools list
all_tools = [
    get_schedule,
    check_squad_scheduled,
    count_active_crews,
    parse_time_reference,
    check_member_availability,  # New tool
]
```

The LLM will automatically learn to use new tools based on their descriptions!

## Further Reading

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools Guide](https://python.langchain.com/docs/modules/agents/tools/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use)

## Support

For issues or questions about the agentic implementation:
1. Check logs: `logs/station95chatbot.log`
2. Run test suite: `python test_agentic.py`
3. Review this guide
4. Check the code comments in `agentic_processor.py`
