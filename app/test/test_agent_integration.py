
import json
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

import graph_agent


class FakeToolCallingLLM:
    """Provides controlled LLM responses without calling Groq."""

    def __init__(self):
        self.invocations = 0
        self.received_tool_result = False

    def invoke(self, messages):

        self.invocations += 1

        # First LLM call: request a product search.
        if self.invocations == 1:

            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_product_tool",
                        "args": {
                            "category": "honey",
                            "max_price": 20,
                            "sort_by": "price_asc",
                        },
                        "id": "integration-test-call-1",
                        "type": "tool_call",
                    }
                ],
            )

        # Second LLM call: verify that the tool result arrived.
        tool_messages = [
            message
            for message in messages
            if isinstance(message, ToolMessage)
        ]

        if not tool_messages:
            raise AssertionError(
                "LLM did not receive the product tool result."
            )

        self.received_tool_result = True

        return AIMessage(
            content="I found honey products under $20."
        )


def test_agent_search_integration():

    # Ensure the customer memory table exists.
    graph_agent.create_memory_table()

    # Use unique IDs to keep this test isolated.
    unique_id = uuid4().hex

    user_id = f"integration-test-{unique_id}"
    thread_id = f"integration-thread-{unique_id}"

    fake_llm = FakeToolCallingLLM()

    # Save the original model.
    original_llm = graph_agent.llm_with_tools

    # Replace only the LLM.
    graph_agent.llm_with_tools = fake_llm

    try:

        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            },
        }

        with graph_agent.trace_context():

            with graph_agent.trace_span("integration_test"):

                result = graph_agent.graph.invoke(
                    {
                        "messages": [
                            HumanMessage(
                                content="Find honey under $20."
                            )
                        ]
                    },
                    config,
                )

        messages = result["messages"]

        # --------------------------------
        # Check 1: Tool was executed.
        # --------------------------------

        tool_messages = [
            message
            for message in messages
            if isinstance(message, ToolMessage)
        ]

        assert len(tool_messages) == 1

        tool_result = tool_messages[0]

        assert tool_result.name == "search_product_tool"

        # --------------------------------
        # Check 2: Database results satisfy
        # the requested constraints.
        # --------------------------------

        products = json.loads(tool_result.content)

        assert isinstance(products, list)
        assert len(products) > 0

        for product in products:

            assert product["category"].lower() == "honey"

            assert product["price"] <= 20

        # --------------------------------
        # Check 3: LLM received tool result.
        # --------------------------------

        assert fake_llm.received_tool_result is True

        # --------------------------------
        # Check 4: LLM completed workflow.
        # --------------------------------

        assert fake_llm.invocations == 2

        final_message = messages[-1]

        assert isinstance(final_message, AIMessage)

        assert final_message.content == (
            "I found honey products under $20."
        )

        print("PASSED: Graph executed successfully")
        print("PASSED: Correct product tool executed")
        print("PASSED: Product results respect budget")
        print("PASSED: LLM received the tool result")
        print("PASSED: Final response generated")

    finally:

        # Always restore the real model.
        graph_agent.llm_with_tools = original_llm


if __name__ == "__main__":

    test_agent_search_integration()

    print("\nAll integration tests passed!")
