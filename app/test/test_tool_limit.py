from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END, MessagesState

from graph_agent import (
    MAX_TOOL_CALLS_PER_TURN,
    should_continue,
    tool_limit_node
)


def create_tool_calls(number):
    return [
        {
            "name": "search_product_tool",
            "args": {"category": "honey"},
            "id": f"test-call-{i}",
            "type": "tool_call"
        }
        for i in range(number)
    ]


# Test 1: Exactly five calls should be allowed.
state_five = {
    "messages": [
        HumanMessage(content="Find honey products."),
        AIMessage(content="", tool_calls=create_tool_calls(5))
    ]
}

assert should_continue(state_five) == "tools"
print("Five tool calls: Allowed")


# Test 2: Six calls should be rejected.
state_six = {
    "messages": [
        HumanMessage(content="Find honey products."),
        AIMessage(content="", tool_calls=create_tool_calls(6))
    ]
}

# Build a small graph to test the rejection node.
builder = StateGraph(MessagesState)

builder.add_node("llm", lambda state: {})
builder.add_node("tool_limit", tool_limit_node)

builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", should_continue)
builder.add_edge("tool_limit", END)

test_graph = builder.compile()

result = test_graph.invoke(state_six)

tool_responses = [
    message
    for message in result["messages"]
    if isinstance(message, ToolMessage)
]

final_message = result["messages"][-1]

assert len(tool_responses) == 6
assert "maximum of 5 tool calls" in final_message.content

print("Six tool calls: Rejected")
print("Tool execution limit test: PASSED")