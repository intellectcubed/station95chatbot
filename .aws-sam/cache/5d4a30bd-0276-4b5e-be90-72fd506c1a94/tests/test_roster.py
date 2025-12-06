"""Tests for roster management."""

import json
import tempfile
from pathlib import Path

import pytest

from src.station95chatbot.roster import Roster, Member


@pytest.fixture
def sample_roster_file():
    """Create a temporary roster file for testing."""
    roster_data = {
        "members": [
            {
                "name": "George Nowakowski",
                "title": "Chief",
                "squad": 43,
                "groupme_name": "George Nowakowski",
            },
            {
                "name": "Katie Sowden",
                "title": "Chief",
                "squad": 35,
                "groupme_name": "Katie Sowden",
            },
            {
                "name": "Jim R",
                "title": "Member",
                "squad": 43,
                "groupme_name": "Jim R",
            },
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(roster_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


def test_roster_load(sample_roster_file):
    """Test loading roster from file."""
    roster = Roster(sample_roster_file)
    assert len(roster.members) == 3


def test_find_member_by_name(sample_roster_file):
    """Test finding a member by name."""
    roster = Roster(sample_roster_file)

    member = roster.find_member_by_name("George Nowakowski")
    assert member is not None
    assert member.squad == 43
    assert member.title == "Chief"

    # Test case-insensitive
    member = roster.find_member_by_name("george nowakowski")
    assert member is not None

    # Test non-existent member
    member = roster.find_member_by_name("Non Existent")
    assert member is None


def test_is_authorized(sample_roster_file):
    """Test authorization check."""
    roster = Roster(sample_roster_file)

    assert roster.is_authorized("George Nowakowski") is True
    assert roster.is_authorized("Katie Sowden") is True
    assert roster.is_authorized("Random Person") is False


def test_get_member_squad(sample_roster_file):
    """Test getting member's squad."""
    roster = Roster(sample_roster_file)

    assert roster.get_member_squad("George Nowakowski") == 43
    assert roster.get_member_squad("Katie Sowden") == 35
    assert roster.get_member_squad("Random Person") is None


def test_get_member_role(sample_roster_file):
    """Test getting member's role."""
    roster = Roster(sample_roster_file)

    assert roster.get_member_role("George Nowakowski") == "Chief"
    assert roster.get_member_role("Jim R") == "Member"
    assert roster.get_member_role("Random Person") is None
