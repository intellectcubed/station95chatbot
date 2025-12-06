"""Agentic AI processor using LangGraph for complex multi-step workflows."""

import json
import logging
import operator
from datetime import datetime
from typing import Annotated, TypedDict, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .calendar_client import CalendarClient
from .config import settings
from .groupme_client import GroupMeClient
from .models import CalendarCommand
from .tools import all_tools

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================


class AgentState(TypedDict):
    """State that flows through the agent workflow."""

    # Input
    original_message: str
    sender_name: str
    sender_squad: int | None
    sender_role: str | None
    message_timestamp: int

    # Conversation with LLM
    messages: Annotated[list, operator.add]  # Accumulates messages

    # Data gathered during execution
    schedule_data: dict  # Calendar data fetched from API
    parsed_requests: list[dict]  # List of sub-requests extracted from message

    # Validation results
    warnings: list[str]  # Warnings to send to group chat
    critical_warnings: list[str]  # Critical warnings (e.g., station out of service)
    validation_passed: bool  # Whether validations passed

    # Execution
    commands_to_execute: list[dict]  # Commands to execute
    execution_results: list[dict]  # Results of command execution

    # Control flow
    next_step: str  # Used for conditional routing
    is_shift_request: bool  # Whether this is a shift request at all
    confidence: int  # Confidence in the interpretation


# ============================================================================
# NODE IMPLEMENTATIONS
# ============================================================================


def interpret_message_node(state: AgentState) -> AgentState:
    """
    Node 1: Use LLM with tools to interpret the message and plan actions.

    This is where the LLM makes tool calls in a loop to gather information.
    """
    logger.info("🤖 Node: Interpret Message")

    # Initialize LLM based on provider
    if settings.ai_provider == "openai":
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
            api_key=settings.openai_api_key
        )
    elif settings.ai_provider == "anthropic":
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
            api_key=settings.anthropic_api_key
        )
    else:
        raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")

    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(all_tools)

    # Build system prompt
    message_time = datetime.fromtimestamp(state["message_timestamp"])
    current_date = message_time.strftime("%Y-%m-%d %H:%M:%S")

    system_prompt = f"""You are an intelligent rescue squad shift management assistant.

**Current Context:**
- Current Date/Time: {current_date}
- Sender: {state["sender_name"]}
- Sender's Squad: {state["sender_squad"] or "Unknown"}
- Sender's Role: {state["sender_role"] or "Unknown"}

**Your Task:**
Analyze the message and use the available tools to:
1. Check the current schedule for relevant dates and squads
2. Verify that requested changes make sense
3. Identify any warnings or conflicts
4. Extract the list of commands to execute

**Available Tools:**
- get_schedule: Fetch current schedule for a date range
- check_squad_scheduled: Check if a specific squad is scheduled
- count_active_crews: Count how many crews are active during a shift
- parse_time_reference: Parse natural language time references

**Important Rules:**
1. ALWAYS check the schedule before making recommendations
2. If removing a crew would leave zero crews on duty, add a CRITICAL warning
3. If a user expects a squad to be scheduled but it's not (or vice versa), add a warning
4. Parse complex messages that contain multiple requests
5. For each action (noCrew, addShift, obliterateShift), verify it's appropriate

**Response Format:**
After using tools to gather information, respond with a JSON object:
{{
    "is_shift_request": true/false,
    "confidence": 0-100,
    "parsed_requests": [
        {{"action": "noCrew", "squad": 42, "date": "20251203", "shift_start": "0000", "shift_end": "0600"}},
        ...
    ],
    "warnings": ["Warning message 1", ...],
    "critical_warnings": ["Critical warning 1", ...],
    "reasoning": "Explanation of your analysis"
}}

**Message to analyze:**
"{state["original_message"]}"

Begin by using the tools to check the schedule, then provide your analysis.
"""

    # Initialize messages if not present
    if not state.get("messages"):
        state["messages"] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["original_message"])
        ]

    # Call LLM with tools - it will make tool calls in a loop
    try:
        response = llm_with_tools.invoke(state["messages"])
        state["messages"].append(response)

        # Check if there are tool calls to execute
        if hasattr(response, "tool_calls") and response.tool_calls:
            # Create tool node to execute tools
            tool_node = ToolNode(all_tools)

            # Execute all tool calls
            for tool_call in response.tool_calls:
                logger.info(f"🔧 Executing tool: {tool_call['name']}")

            # Execute tools and get results
            tool_results = tool_node.invoke({"messages": state["messages"]})

            # Add tool results to messages
            if "messages" in tool_results:
                state["messages"].extend(tool_results["messages"])

                # Add explicit prompt for JSON response
                state["messages"].append(
                    HumanMessage(content="Based on the tool results above, provide your complete analysis in the required JSON format as specified in the system prompt.")
                )

                # Call LLM again with tool results to get final analysis
                final_response = llm.invoke(state["messages"])
                state["messages"].append(final_response)
                response = final_response

        # Extract the final analysis from the response
        content = response.content if hasattr(response, "content") else str(response)

        # Try to parse JSON from the response
        try:
            # Look for JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            logger.info('+'*60)
            logger.info(content)
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                analysis = json.loads(json_str)

                logger.info(f"🔍 LLM Response: {response}")  # Add this
                logger.info("🔍 Extracting JSON from LLM response")

                state["is_shift_request"] = analysis.get("is_shift_request", False)
                state["confidence"] = analysis.get("confidence", 0)
                state["parsed_requests"] = analysis.get("parsed_requests", [])
                state["warnings"] = analysis.get("warnings", [])
                state["critical_warnings"] = analysis.get("critical_warnings", [])

                logger.info(f"✅ Parsed {len(state['parsed_requests'])} requests")
                logger.info(f"⚠️  Generated {len(state['warnings'])} warnings")
                logger.info(f"🚨 Generated {len(state['critical_warnings'])} critical warnings")
            else:
                # No JSON found, treat as non-shift request
                state["is_shift_request"] = False
                state["confidence"] = 0
                state["parsed_requests"] = []
                state["warnings"] = []
                state["critical_warnings"] = []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            state["is_shift_request"] = False
            state["confidence"] = 0
            state["parsed_requests"] = []
            state["warnings"] = ["Error: Failed to interpret message"]
            state["critical_warnings"] = []

    except Exception as e:
        logger.error(f"Error in interpret_message_node: {e}")
        state["is_shift_request"] = False
        state["confidence"] = 0
        state["parsed_requests"] = []
        state["warnings"] = [f"Error interpreting message: {str(e)}"]
        state["critical_warnings"] = []

    return state


def validate_changes_node(state: AgentState) -> AgentState:
    """
    Node 2: Validate that the requested changes won't cause problems.

    This does additional validation beyond what the LLM did.
    """
    logger.info("🔍 Node: Validate Changes")

    # Set commands to execute from parsed requests
    state["commands_to_execute"] = state["parsed_requests"]

    # Additional validation logic can go here
    # For now, we rely on the LLM's analysis

    # Decide if we should proceed
    # You could add logic here to block execution if critical warnings exist
    state["validation_passed"] = True

    logger.info(f"Validation {'PASSED' if state['validation_passed'] else 'FAILED'}")

    return state


def send_warnings_node(state: AgentState) -> AgentState:
    """
    Node 3: Send warnings to the GroupMe chat.
    """
    all_warnings = state.get("warnings", []) + state.get("critical_warnings", [])

    logger.info(f"⚠️  Node: Send Warnings ({len(all_warnings)} warnings)")

    if all_warnings:
        try:
            groupme = GroupMeClient()

            # Send critical warnings first
            for warning in state.get("critical_warnings", []):
                groupme.send_critical_alert(warning)

            # Then send regular warnings
            for warning in state.get("warnings", []):
                groupme.send_warning(warning)

            logger.info("✅ Warnings sent to group chat")

        except Exception as e:
            logger.error(f"Failed to send warnings: {e}")

    return state


def execute_commands_node(state: AgentState) -> AgentState:
    """
    Node 4: Execute the calendar commands.
    """
    commands = state.get("commands_to_execute", [])
    logger.info(f"⚡ Node: Execute Commands ({len(commands)} commands)")

    calendar_client = CalendarClient()
    results = []

    for request in commands:
        if request.get("action") in ["noCrew", "addShift", "obliterateShift"]:
            try:
                command = CalendarCommand(
                    action=request["action"],
                    squad=request["squad"],
                    date=request["date"],
                    shift_start=request["shift_start"],
                    shift_end=request["shift_end"],
                    preview=False
                )

                response = calendar_client.send_command(command)

                results.append({
                    "command": request,
                    "status": "success",
                    "response": response
                })

                logger.info(f"✅ Executed: {request['action']} for Squad {request['squad']}")

            except Exception as e:
                results.append({
                    "command": request,
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"❌ Failed: {request['action']} - {e}")

    state["execution_results"] = results
    return state


# ============================================================================
# CONDITIONAL EDGES (routing logic)
# ============================================================================


def route_after_interpret(state: AgentState) -> Literal["validate", "end"]:
    """Decide whether to proceed with validation or end."""
    # If not a shift request or confidence too low, end
    if not state.get("is_shift_request", False):
        logger.info("Not a shift request, ending workflow")
        return "end"

    if state.get("confidence", 0) < settings.confidence_threshold:
        logger.info(f"Confidence too low ({state.get('confidence')}), ending workflow")
        return "end"

    # If no commands to execute, end
    if not state.get("parsed_requests"):
        logger.info("No commands to execute, ending workflow")
        return "end"

    logger.info("Proceeding to validation")
    return "validate"


def route_after_validate(state: AgentState) -> Literal["send_warnings", "execute", "end"]:
    """Decide whether to send warnings, execute, or end."""
    if not state.get("validation_passed", True):
        logger.info("Validation failed, ending workflow")
        return "end"

    # If there are warnings, send them first
    all_warnings = state.get("warnings", []) + state.get("critical_warnings", [])
    if all_warnings:
        logger.info("Warnings present, will send warnings before executing")
        return "send_warnings"

    # No warnings, proceed to execution
    logger.info("No warnings, proceeding to execution")
    return "execute"


# ============================================================================
# BUILD THE GRAPH
# ============================================================================


def create_agentic_workflow() -> StateGraph:
    """Create and compile the LangGraph workflow."""

    # Initialize the graph with our state type
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("interpret", interpret_message_node)
    workflow.add_node("validate", validate_changes_node)
    workflow.add_node("send_warnings", send_warnings_node)
    workflow.add_node("execute", execute_commands_node)

    # Set entry point
    workflow.set_entry_point("interpret")

    # Add edges
    # interpret → validate OR end (conditional)
    workflow.add_conditional_edges(
        "interpret",
        route_after_interpret,
        {
            "validate": "validate",
            "end": END
        }
    )

    # validate → send_warnings OR execute OR end (conditional)
    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "send_warnings": "send_warnings",
            "execute": "execute",
            "end": END
        }
    )

    # send_warnings → execute (always)
    workflow.add_edge("send_warnings", "execute")

    # execute → END (always)
    workflow.add_edge("execute", END)

    # Compile the graph
    return workflow.compile()


# ============================================================================
# MAIN PROCESSOR CLASS
# ============================================================================


class AgenticProcessor:
    """Agentic processor using LangGraph for complex multi-step workflows."""

    def __init__(self):
        """Initialize the agentic processor."""
        self.workflow = create_agentic_workflow()
        logger.info("Initialized AgenticProcessor with LangGraph workflow")

    def process_message(
        self,
        message_text: str,
        sender_name: str,
        sender_squad: int | None,
        sender_role: str | None,
        message_timestamp: int
    ) -> dict:
        """
        Process a message through the agentic workflow.

        Args:
            message_text: The message text to process
            sender_name: Name of the sender
            sender_squad: Squad number of the sender (if known)
            sender_role: Role of the sender (if known)
            message_timestamp: Unix timestamp of the message

        Returns:
            Dictionary with processing results
        """
        logger.info(f"🚀 Starting agentic workflow for message: {message_text[:50]}...")

        # Initial state
        initial_state: AgentState = {
            "original_message": message_text,
            "sender_name": sender_name,
            "sender_squad": sender_squad,
            "sender_role": sender_role,
            "message_timestamp": message_timestamp,
            "messages": [],
            "schedule_data": {},
            "parsed_requests": [],
            "warnings": [],
            "critical_warnings": [],
            "validation_passed": True,
            "commands_to_execute": [],
            "execution_results": [],
            "next_step": "",
            "is_shift_request": False,
            "confidence": 0
        }

        # Run the workflow
        try:
            final_state = self.workflow.invoke(initial_state)

            logger.info("✅ Workflow complete")

            return {
                "is_shift_request": final_state.get("is_shift_request", False),
                "confidence": final_state.get("confidence", 0),
                "parsed_requests": final_state.get("parsed_requests", []),
                "warnings": final_state.get("warnings", []),
                "critical_warnings": final_state.get("critical_warnings", []),
                "execution_results": final_state.get("execution_results", []),
                "validation_passed": final_state.get("validation_passed", True)
            }

        except Exception as e:
            logger.error(f"Error in agentic workflow: {e}")
            return {
                "is_shift_request": False,
                "confidence": 0,
                "parsed_requests": [],
                "warnings": [f"Error processing message: {str(e)}"],
                "critical_warnings": [],
                "execution_results": [],
                "validation_passed": False
            }
