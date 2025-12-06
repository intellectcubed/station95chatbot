#!/usr/bin/env python3
"""Test script for the agentic AI workflow."""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set agentic mode for testing
os.environ["AI_MODE"] = "agentic"

from station95chatbot.agentic_processor import AgenticProcessor
from station95chatbot import logging_config

# Initialize logging
logging_config.setup_logging()

import logging
logger = logging.getLogger(__name__)


def test_simple_message():
    """Test a simple single-command message."""
    print("\n" + "="*80)
    print("TEST 1: Simple Message")
    print("="*80)

    processor = AgenticProcessor()

    message = "Squad 34 will not have a crew tonight"
    timestamp = int(datetime.now().timestamp())

    print(f"\nMessage: {message}")
    print(f"Timestamp: {timestamp}")

    result = processor.process_message(
        message_text=message,
        sender_name="Test User",
        sender_squad=34,
        sender_role="Chief",
        message_timestamp=timestamp
    )

    print("\n--- RESULT ---")
    print(f"Is shift request: {result['is_shift_request']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Parsed requests: {len(result['parsed_requests'])}")
    for i, req in enumerate(result['parsed_requests'], 1):
        print(f"  {i}. {req['action']} - Squad {req['squad']} - {req['date']} {req['shift_start']}-{req['shift_end']}")
    print(f"Warnings: {result['warnings']}")
    print(f"Critical warnings: {result['critical_warnings']}")
    print(f"Execution results: {len(result['execution_results'])} command(s)")


def test_complex_message():
    """Test a complex multi-command message."""
    print("\n" + "="*80)
    print("TEST 2: Complex Message with Multiple Commands")
    print("="*80)

    processor = AgenticProcessor()

    message = """42 will not have a crew tonight midnight - 6 or Thursday midnight - 6.
    We will add a crew for Saturday morning shift"""
    timestamp = int(datetime.now().timestamp())

    print(f"\nMessage: {message}")
    print(f"Timestamp: {timestamp}")

    result = processor.process_message(
        message_text=message,
        sender_name="Test Chief",
        sender_squad=42,
        sender_role="Chief",
        message_timestamp=timestamp
    )

    print("\n--- RESULT ---")
    print(f"Is shift request: {result['is_shift_request']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Parsed requests: {len(result['parsed_requests'])}")
    for i, req in enumerate(result['parsed_requests'], 1):
        print(f"  {i}. {req['action']} - Squad {req['squad']} - {req['date']} {req['shift_start']}-{req['shift_end']}")
    print(f"\nWarnings: {result['warnings']}")
    print(f"Critical warnings: {result['critical_warnings']}")
    print(f"Execution results: {len(result['execution_results'])} command(s)")


def test_schedule_check_message():
    """Test a message that requires checking the schedule."""
    print("\n" + "="*80)
    print("TEST 3: Message Requiring Schedule Check")
    print("="*80)

    processor = AgenticProcessor()

    message = "Remove Squad 42 from tonight's evening shift"
    timestamp = int(datetime.now().timestamp())

    print(f"\nMessage: {message}")
    print(f"Timestamp: {timestamp}")
    print("\nThis should:")
    print("1. Check current schedule for tonight")
    print("2. Verify Squad 42 is scheduled")
    print("3. Check if removing them leaves any crews on duty")
    print("4. Warn if station would be out of service")

    result = processor.process_message(
        message_text=message,
        sender_name="Test Chief",
        sender_squad=42,
        sender_role="Chief",
        message_timestamp=timestamp
    )

    print("\n--- RESULT ---")
    print(f"Is shift request: {result['is_shift_request']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Parsed requests: {len(result['parsed_requests'])}")
    for i, req in enumerate(result['parsed_requests'], 1):
        print(f"  {i}. {req['action']} - Squad {req['squad']} - {req['date']} {req['shift_start']}-{req['shift_end']}")
    print(f"\nWarnings: {result['warnings']}")
    print(f"Critical warnings: {result['critical_warnings']}")
    print(f"Execution results: {len(result['execution_results'])} command(s)")


def test_non_shift_message():
    """Test a non-shift message."""
    print("\n" + "="*80)
    print("TEST 4: Non-Shift Message")
    print("="*80)

    processor = AgenticProcessor()

    message = "Hey everyone, great job at the training last night!"
    timestamp = int(datetime.now().timestamp())

    print(f"\nMessage: {message}")
    print(f"Timestamp: {timestamp}")

    result = processor.process_message(
        message_text=message,
        sender_name="Test User",
        sender_squad=34,
        sender_role="Member",
        message_timestamp=timestamp
    )

    print("\n--- RESULT ---")
    print(f"Is shift request: {result['is_shift_request']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Parsed requests: {len(result['parsed_requests'])}")


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║           AGENTIC AI WORKFLOW TEST SUITE                              ║")
    print("║           Station 95 Chatbot - LangGraph Implementation               ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print("\n")

    print("NOTE: These tests use PREVIEW mode and won't actually modify the calendar.")
    print("The agentic workflow will:")
    print("  1. Use LLM with tools to analyze the message")
    print("  2. Check the schedule using API calls")
    print("  3. Validate the changes")
    print("  4. Generate warnings if needed")
    print("  5. Execute commands (in preview mode)")
    print("\n")

    try:
        # Run tests
        test_simple_message()
        test_complex_message()
        test_schedule_check_message()
        test_non_shift_message()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        print("\n")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
