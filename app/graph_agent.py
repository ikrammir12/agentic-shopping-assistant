from langgraph.graph import StateGraph, START ,MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from llm import get_llm

from tools.product_tools import check_product_tool, search_product_tool, compare_product_tool


#1= Register the existing python tools

tools = [check_product_tool, search_product_tool,compare_product_tool]

checkpointer = InMemorySaver()

#2= Initialize the LLm and connect tool schemas 
llm = get_llm()
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """
You are a helpful shopping assistant.

Use the available tools to retrieve product information.
Never invent prices, ratings, or product details.
After receiving tool results, provide a clear customer-facing answer.
"""

#3= Define the LLm Node

def call_llm(state:MessagesState):
    """Asked LLm to response or request the tool"""

    response = llm_with_tools.invoke(

        [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"]

        ]
    )

    return {"messages": [response]}


def should_continue(state: MessagesState):
    """
    Decide whether to execute tools or end the workflow.
    """

    messages = state["messages"]

    # Get the latest AI message
    last_message = messages[-1]

    # Check whether the AI requested a tool
    if last_message.tool_calls:
        print("Routing: Tool execution required")
        return "tools"

    # Otherwise, finish the workflow
    print("Routing: No tool call. Ending workflow.")
    return END

#4. Build the Graph

builder = StateGraph(MessagesState)

# 5. Register nodes
builder.add_node("llm", call_llm)
builder.add_node("tools", ToolNode(tools))


# 6. Connect nodes
builder.add_edge(START, "llm")

builder.add_conditional_edges(
    "llm",
    should_continue
)

builder.add_edge("tools", "llm")


# 7. Compile the graph
graph = builder.compile(
    checkpointer=checkpointer
)


# 8. Run the graph
if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "customer-001"
        }
    }

    # First conversation
    result1 = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="My preferred honey budget is $15. Remember it."
                )
            ]
        },
        config
    )

    print("\nFIRST RESPONSE:")
    result1["messages"][-1].pretty_print()

    # Second conversation turn, same thread
    result2 = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What is my preferred budget?"
                )
            ]
        },
        config
    )

    print("\nSECOND RESPONSE:")
    result2["messages"][-1].pretty_print()

    # Inspect saved graph state
snapshot = graph.get_state(config)

print("\n========== SAVED GRAPH STATE ==========")

print("\nThread ID:")
print(snapshot.config["configurable"]["thread_id"])

print("\nSaved Messages:")

for message in snapshot.values["messages"]:
    message.pretty_print()

print("\nNext Nodes:")
print(snapshot.next)

print("\nExecution Metadata:")
print(snapshot.metadata)