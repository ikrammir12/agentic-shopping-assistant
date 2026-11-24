"""Deterministic tests for Blink AI's persistent customer memory."""

import sys
import uuid
from pathlib import Path

# Make the project root importable when this file is run on its own.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app import graph_agent
from app.database.memory import (
    create_memory_table,
    get_customer_preferences,
    save_preference,
)


@pytest.fixture(autouse=True)
def ensure_memory_table():
    """Ensure the preferences table exists before each test."""
    create_memory_table()


def unique_user_id() -> str:
    """Return an isolated test user ID to avoid test-data collisions."""
    return f"memory-eval-{uuid.uuid4()}"


def test_preferences_are_persisted_and_retrieved():
    user_id = unique_user_id()

    save_preference(user_id, "category", "honey")
    save_preference(user_id, "budget", 20)

    preferences = get_customer_preferences(user_id)

    assert preferences == {
        "budget": "20",
        "category": "honey",
    }


def test_saving_existing_preference_updates_value():
    user_id = unique_user_id()

    save_preference(user_id, "budget", 15)
    save_preference(user_id, "budget", 25)

    preferences = get_customer_preferences(user_id)

    assert preferences["budget"] == "25"
    assert len(preferences) == 1


def test_preferences_are_isolated_between_users():
    user_a = unique_user_id()
    user_b = unique_user_id()

    save_preference(user_a, "budget", 20)
    save_preference(user_a, "category", "honey")
    save_preference(user_b, "budget", 50)

    preferences_a = get_customer_preferences(user_a)
    preferences_b = get_customer_preferences(user_b)

    assert preferences_a == {
        "budget": "20",
        "category": "honey",
    }
    assert preferences_b == {"budget": "50"}


def test_capture_preferences_saves_extracted_values(monkeypatch):
    user_id = unique_user_id()

    expected_extraction = graph_agent.PreferenceExtraction(
        preferences=[
            graph_agent.CustomerPreference(key="budget", value="30"),
            graph_agent.CustomerPreference(key="category", value="honey"),
        ]
    )

    class FakePreferenceExtractor:
        def invoke(self, messages):
            return expected_extraction

    monkeypatch.setattr(
        graph_agent,
        "preference_extractor",
        FakePreferenceExtractor(),
    )

    result = graph_agent.capture_preferences(
        {"messages": [HumanMessage(content="I usually buy honey and my budget is $30.")]},
        {"configurable": {"user_id": user_id}},
    )

    assert result == {}
    assert get_customer_preferences(user_id) == {
        "budget": "30",
        "category": "honey",
    }


def test_saved_preferences_are_injected_for_a_new_conversation(monkeypatch):
    user_id = unique_user_id()
    save_preference(user_id, "category", "honey")
    save_preference(user_id, "budget", 20)

    captured_messages = []

    class FakeLLMWithTools:
        def invoke(self, messages):
            captured_messages.extend(messages)
            return AIMessage(content="Mocked final response")

    monkeypatch.setattr(graph_agent, "llm_with_tools", FakeLLMWithTools())

    result = graph_agent.call_llm(
        {"messages": [HumanMessage(content="Find some products.")]},
        {
            "configurable": {
                "thread_id": f"new-thread-{uuid.uuid4()}",
                "user_id": user_id,
            }
        },
    )

    assert result["messages"][0].content == "Mocked final response"

    memory_messages = [
        message.content
        for message in captured_messages
        if isinstance(message, SystemMessage)
        and "Saved customer preferences" in message.content
    ]

    assert len(memory_messages) == 1
    assert "category: honey" in memory_messages[0]
    assert "budget: 20" in memory_messages[0]


def test_empty_user_id_is_rejected():
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        get_customer_preferences("   ")

    with pytest.raises(ValueError, match="user_id cannot be empty"):
        save_preference("   ", "budget", 20)
