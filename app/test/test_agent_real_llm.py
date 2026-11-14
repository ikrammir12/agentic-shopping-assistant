
import json
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

import graph_agent


def test_real_llm_shopping_workflow():

    graph_agent.create_memory_table()

    unique_id = uuid4().hex

    config = {
        "recursion_limit": 20,
        "configurable": {
            "thread_id": f"real-llm-{unique_id}",
            "user_id": f"real-user-{unique_id}",
        },
    }

    user_request = """
    Search for honey products.

    Use search_product_tool with:
    category = honey
    max_price = 20
    sort_by = price_asc

    Do not use any other tool.
    Recommend products only from the returned results.
    """

    # Execute the actual graph and actual Groq model.
    with graph_agent.trace_context():

        with graph_agent.trace_span("real_llm_evaluation"):

            result = graph_agent.graph.invoke(
                {
                    "messages": [
                        HumanMessage(content=user_request)
                    ]
                },
                config,
            )

    messages = result["messages"]

    # --------------------------------
    # Check 1: Did the LLM call a tool?
    # --------------------------------

    tool_call_messages = [
        message
        for message in messages
        if isinstance(message, AIMessage)
        and getattr(message, "tool_calls", [])
    ]

    assert tool_call_messages, "LLM did not request a tool."

    all_tool_calls = [
        call
        for message in tool_call_messages
        for call in message.tool_calls
    ]

    assert len(all_tool_calls) == 1, (
        f"Expected one tool call, received {len(all_tool_calls)}"
    )

    selected_call = all_tool_calls[0]

    assert selected_call["name"] == "search_product_tool"

    print("PASSED: Correct tool selected")

    # --------------------------------
    # Check 2: Were correct arguments
    # passed by the LLM?
    # --------------------------------

    arguments = selected_call["args"]

    assert arguments["category"].lower() == "honey"
    assert arguments["max_price"] == 20
    assert arguments["sort_by"] == "price_asc"

    print("PASSED: Correct tool arguments")

    # --------------------------------
    # Check 3: Did the tool execute?
    # --------------------------------

    tool_results = [
        message
        for message in messages
        if isinstance(message, ToolMessage)
        and message.name == "search_product_tool"
    ]

    assert len(tool_results) == 1

    products = json.loads(tool_results[0].content)

    assert isinstance(products, list)
    assert len(products) > 0

    assert all(
        product["price"] <= 20
        for product in products
    )

    prices = [product["price"] for product in products]

    assert prices == sorted(prices)

    print("PASSED: Tool returned valid products")

    # --------------------------------
    # Check 4: Did the agent complete?
    # --------------------------------

    final_message = messages[-1]

    assert isinstance(final_message, AIMessage)
    assert isinstance(final_message.content, str)
    assert final_message.content.strip()

    print("PASSED: Final AI response generated")

    # Display final response for manual evaluation.
    print("\n========== FINAL AI RESPONSE ==========")
    print(final_message.content)

    print("\nAll real LLM workflow checks passed!")


if __name__ == "__main__":
    test_real_llm_shopping_workflow()
