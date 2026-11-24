import sys
from pathlib import Path

# Add project root to Python import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import json
import uuid
from typing import Any

import pytest
from langchain_core.messages import HumanMessage
from app.graph_agent import graph


# ==========================================
# 1. DATASET CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    PROJECT_ROOT
    / "evals"
    / "datasets"
    / "shopping_agent_v1.jsonl"
)


def load_dataset() -> list[dict[str, Any]]:
    """Load one JSON test case per line."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    cases = []

    with DATASET_PATH.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):

            if not line.strip():
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}: {exc}"
                ) from exc

            cases.append(case)

    if not cases:
        raise ValueError("Evaluation dataset contains no test cases.")

    return cases


# ==========================================
# 2. TOOL RESULT PARSER
# ==========================================

def parse_tool_result(content: Any) -> Any:
    """Convert serialized tool output into Python data."""

    if not isinstance(content, str):
        return content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


# ==========================================
# 3. EVALUATION TEST
# ==========================================

def get_case_id(case: dict[str, Any]) -> str:
    return case.get("metadata", {}).get(
        "case_id",
        "unnamed-test"
    )


@pytest.mark.parametrize(
    "case",
    load_dataset(),
    ids=get_case_id
)
def test_agent_execution(case: dict[str, Any]):

    case_id = get_case_id(case)

    message = case["inputs"]["message"]
    expected = case["outputs"]

    # Use a unique user and thread for each test.
    # This prevents one evaluation case from contaminating another.
    user_id = f"eval-{uuid.uuid4()}"

    thread_id = f"{case_id}-{uuid.uuid4()}"

    config = {
        "recursion_limit": 20,
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        },
    }

    # ======================================
    # RUN THE REAL LANGGRAPH AGENT
    # ======================================

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=message)
            ]
        },
        config=config,
    )

    messages = result.get("messages", [])

    assert messages, "Agent returned no messages."

    # ======================================
    # EXTRACT ACTUAL TOOL CALLS
    # ======================================

    actual_tool_calls = []
    tool_results = {}

    for item in messages:

        # Capture LLM-generated tool calls.
        for tool_call in getattr(item, "tool_calls", []) or []:

            actual_tool_calls.append({
                "name": tool_call.get("name"),
                "arguments": tool_call.get("args", {}),
            })

        # Capture actual tool responses.
        if getattr(item, "type", None) == "tool":

            tool_name = getattr(
                item,
                "name",
                "unknown_tool"
            )

            tool_results.setdefault(tool_name, []).append(
                parse_tool_result(item.content)
            )

    actual_tool_names = [
        call["name"]
        for call in actual_tool_calls
    ]

    expected_tool_names = expected["expected_tools"]

    # ======================================
    # EVALUATOR 1: TOOL SELECTION ACCURACY
    # ======================================

    assert actual_tool_names == expected_tool_names, (
        f"{case_id}: Incorrect tool selection.\n"
        f"Expected: {expected_tool_names}\n"
        f"Actual: {actual_tool_names}"
    )

    # ======================================
    # EVALUATOR 2: TOOL ARGUMENT ACCURACY
    # ======================================

    expected_arguments = expected.get(
        "expected_arguments",
        {}
    )

    for expected_tool in expected_tool_names:

        matching_calls = [
            call for call in actual_tool_calls
            if call["name"] == expected_tool
        ]

        assert matching_calls, (
            f"{case_id}: Expected tool was not called: {expected_tool}"
        )

        actual_arguments = matching_calls[0]["arguments"]

        for key, expected_value in expected_arguments.items():

            assert actual_arguments.get(key) == expected_value, (
                f"{case_id}: Incorrect argument '{key}'. "
                f"Expected {expected_value!r}, "
                f"got {actual_arguments.get(key)!r}"
            )

    # ======================================
    # EVALUATOR 3: TOOL EXECUTION SUCCESS
    # ======================================

    for expected_tool in expected_tool_names:

        assert expected_tool in tool_results, (
            f"{case_id}: Tool was selected but no tool response was found: "
            f"{expected_tool}"
        )

        assert tool_results[expected_tool], (
            f"{case_id}: Tool returned no results."
        )

        for tool_output in tool_results[expected_tool]:

            if isinstance(tool_output, dict):
                assert not tool_output.get("error"), (
                    f"{case_id}: Tool returned an error: {tool_output}"
                )

    # ======================================
    # EVALUATOR 4: PRODUCT RESULT ACCURACY
    # ======================================

    expected_product_ids = expected.get(
        "expected_product_ids"
    )

    search_results = tool_results.get(
        "search_product_tool",
        []
    )

    if expected_product_ids is not None:

        actual_products = []

        for output in search_results:
            if isinstance(output, list):
                actual_products.extend(
                    product
                    for product in output
                    if isinstance(product, dict)
                )

        actual_product_ids = [
            product["id"]
            for product in actual_products
            if product.get("id") is not None
        ]

        assert actual_product_ids == expected_product_ids, (
            f"{case_id}: Product results do not match.\n"
            f"Expected IDs: {expected_product_ids}\n"
            f"Actual IDs: {actual_product_ids}"
        )

        # Verify price, category and organic constraints.
        constraints = expected.get(
            "expected_constraints",
            {}
        )

        for product in actual_products:

            if "maximum_price" in constraints:
                assert product["price"] <= constraints["maximum_price"]

            if "category" in constraints:
                assert (
                    product["category"].lower()
                    == constraints["category"].lower()
                )

            if constraints.get("organic_only"):
                assert product["is_organic"] == 1

    # ======================================
    # EVALUATOR 5: FINAL ANSWER
    # ======================================

    final_message = messages[-1]

    assert getattr(final_message, "type", None) == "ai", (
        f"{case_id}: Final message is not an AI response."
    )

    assert getattr(final_message, "content", None), (
        f"{case_id}: Agent returned an empty final answer."
    )

    # ======================================
    # EVALUATION SUMMARY
    # ======================================

    print(f"\n{'=' * 45}")
    print(f"Evaluation: {case_id}")
    print(f"Status: PASSED")
    print(f"Expected tools: {expected_tool_names}")
    print(f"Actual tools: {actual_tool_names}")
    print(f"Products found: {expected_product_ids}")
    print(f"{'=' * 45}")
