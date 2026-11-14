
import sqlite3

from langchain.tools import tool
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

from graph_agent import fun_to_handle_tool_error


# Simulate a database error
@tool
def database_failure_tool() -> str:
    """Simulate a database failure."""
    raise sqlite3.OperationalError("no such table: products")


# Simulate invalid customer input
@tool
def invalid_input_tool() -> str:
    """Simulate invalid customer input."""
    raise ValueError("Budget must be positive.")


def run_tool_test(tool_instance):

    # Create a small graph
    builder = StateGraph(MessagesState)

    # Add ToolNode with our custom error handler
    builder.add_node(
        "tools",
        ToolNode(
            [tool_instance],
            handle_tool_errors=fun_to_handle_tool_error
        )
    )

    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)

    graph = builder.compile()

    # Simulate an LLM tool call
    result = graph.invoke({
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": tool_instance.name,
                        "args": {},
                        "id": "test-call-001",
                        "type": "tool_call"
                    }
                ]
            )
        ]
    })

    print(result["messages"][-1].content)


if __name__ == "__main__":

    print("\n--- Testing SQLite error ---")
    run_tool_test(database_failure_tool)

    print("\n--- Testing ValueError ---")
    run_tool_test(invalid_input_tool)


@tool
def unexpected_failure_tool() -> str:
    """Simulate an unexpected programming error."""
    raise RuntimeError("Simulated programming bug")
print("\n--- Testing unexpected error ---")

try:
    run_tool_test(unexpected_failure_tool)

except RuntimeError as error:
    print("Unexpected error propagated:", error)