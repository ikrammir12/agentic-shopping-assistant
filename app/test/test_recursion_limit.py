from typing import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.errors import GraphRecursionError


class CounterState(TypedDict):
    count: int


def first_node(state: CounterState):
    print("First node:", state["count"])
    return {"count": state["count"] + 1}


def second_node(state: CounterState):
    print("Second node:", state["count"])
    return {"count": state["count"] + 1}


builder = StateGraph(CounterState)

builder.add_node("first", first_node)
builder.add_node("second", second_node)

builder.add_edge(START, "first")
builder.add_edge("first", "second")
builder.add_edge("second", "first")

loop_graph = builder.compile()

try:
    loop_graph.invoke(
        {"count": 0},
        {"recursion_limit": 4}
    )

except GraphRecursionError:
    print("\nSUCCESS: Recursion limit stopped the infinite loop.")