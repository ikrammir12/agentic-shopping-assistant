from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


# 1. Define the graph state
class OrderState(TypedDict, total=False):
    product_name: str
    quantity: int
    approved: bool
    status: str


# 2. Human approval node
def human_review(state: OrderState):

    # Pause execution and request human approval
    decision = interrupt({
        "message": "Approval required before placing this order.",
        "product": state["product_name"],
        "quantity": state["quantity"],
        "action": "Place order"
    })

    return {"approved": decision}


# 3. Route based on human decision
def route_after_review(state: OrderState):

    if state["approved"]:
        return "place_order"

    return "cancel_order"


# 4. Simulated order execution
def place_order(state: OrderState):

    print("\nExecuting simulated order...")

    return {
        "status": "SIMULATED_ORDER_PLACED"
    }


# 5. Rejected order
def cancel_order(state: OrderState):

    print("\nOrder rejected by human.")

    return {
        "status": "ORDER_CANCELLED"
    }


# 6. Build graph
builder = StateGraph(OrderState)

builder.add_node("human_review", human_review)
builder.add_node("place_order", place_order)
builder.add_node("cancel_order", cancel_order)

builder.add_edge(START, "human_review")

builder.add_conditional_edges(
    "human_review",
    route_after_review
)

builder.add_edge("place_order", END)
builder.add_edge("cancel_order", END)


# 7. Compile with checkpointer
checkpointer = InMemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)


# 8. Execute and resume
if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "order-approval-001"
        }
    }

    result = graph.invoke(
        {
            "product_name": "Organic Raw Honey",
            "quantity": 2
        },
        config
    )

    # Check whether execution was interrupted
    pending = result.get("__interrupt__", ())

    if pending:

        print("\n========== HUMAN APPROVAL REQUIRED ==========")

        for item in pending:
            print(item.value)

        while True:
            decision = input(
                "\nApprove this order? (yes/no): "
            ).strip().lower()

            if decision in ("yes", "no"):
                break

            print("Please enter yes or no.")

        # Resume the graph with human decision
        final_result = graph.invoke(
            Command(resume=(decision == "yes")),
            config
        )

        print("\n========== FINAL RESULT ==========")
        print(final_result)

if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())
png_data = graph.get_graph().draw_mermaid_png()

with open("order_approval_graph.png", "wb") as f:
    f.write(png_data)