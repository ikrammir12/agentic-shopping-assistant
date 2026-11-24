"""Run Blink AI's agent against the LangSmith evaluation dataset."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langsmith import Client
from langsmith.evaluation import run_evaluator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
DATASET_NAME = "blink-ai-shopping-v1"


def parse_tool_content(content: Any) -> Any:
    """Decode JSON tool output when the ToolMessage contains JSON text."""
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return content


def collect_products(value: Any) -> list[dict[str, Any]]:
    """Find product-like dictionaries inside nested tool output."""
    found: list[dict[str, Any]] = []

    def visit(item: Any) -> None:
        if isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            if "id" in item and ("name" in item or "price" in item):
                found.append(item)
            else:
                for child in item.values():
                    visit(child)

    visit(value)
    return found


def build_target(graph):
    """Create a LangSmith target function around the real LangGraph agent."""

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        message = inputs.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Dataset input must contain a non-empty 'message'.")

        # Isolate each evaluation example from all other users and threads.
        user_id = f"langsmith-eval-{uuid.uuid4()}"
        thread_id = f"langsmith-eval-{uuid.uuid4()}"
        config = {
            "recursion_limit": 20,
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            },
        }

        result = graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        messages = result.get("messages", [])

        tool_calls: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        all_products: list[dict[str, Any]] = []
        final_answer = ""

        for item in messages:
            if isinstance(item, AIMessage):
                for call in getattr(item, "tool_calls", []) or []:
                    tool_calls.append(
                        {
                            "name": call.get("name"),
                            "arguments": call.get("args", {}),
                        }
                    )
                if isinstance(item.content, str) and item.content.strip():
                    final_answer = item.content

            if isinstance(item, ToolMessage):
                decoded = parse_tool_content(item.content)
                tool_results.append(
                    {
                        "name": getattr(item, "name", "unknown_tool"),
                        "result": decoded,
                    }
                )
                if getattr(item, "name", None) == "search_product_tool":
                    all_products.extend(collect_products(decoded))

        # Remove duplicate product rows while retaining order.
        seen_ids: set[Any] = set()
        unique_product_ids: list[Any] = []
        for product in all_products:
            product_id = product.get("id")
            if product_id is not None and product_id not in seen_ids:
                seen_ids.add(product_id)
                unique_product_ids.append(product_id)

        return {
            "answer": final_answer,
            "tool_names": [call["name"] for call in tool_calls],
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "product_ids": unique_product_ids,
        }

    return target


@run_evaluator
def tool_selection_evaluator(run, example) -> dict[str, Any]:
    reference = example.outputs or {}
    expected = reference.get("expected_tools", [])
    actual = (run.outputs or {}).get("tool_names", [])
    passed = actual == expected
    return {
        "key": "tool_selection_accuracy",
        "score": passed,
        "comment": f"Expected {expected}; got {actual}.",
    }


@run_evaluator
def tool_argument_evaluator(run, example) -> dict[str, Any]:
    reference = example.outputs or {}
    expected_tools = reference.get("expected_tools", [])
    expected_arguments = reference.get("expected_arguments", {})

    if not expected_arguments:
        return {
            "key": "tool_argument_accuracy",
            "value": "not_applicable",
            "comment": "No expected arguments were defined for this example.",
        }

    actual_calls = (run.outputs or {}).get("tool_calls", [])
    errors: list[str] = []

    for tool_name in expected_tools:
        matching = [call for call in actual_calls if call.get("name") == tool_name]
        if not matching:
            errors.append(f"Expected tool was not called: {tool_name}")
            continue

        actual_arguments = matching[0].get("arguments", {})
        for key, expected_value in expected_arguments.items():
            actual_value = actual_arguments.get(key)
            if actual_value != expected_value:
                errors.append(
                    f"{tool_name}.{key}: expected {expected_value!r}, got {actual_value!r}"
                )

    return {
        "key": "tool_argument_accuracy",
        "score": not errors,
        "comment": "All expected arguments matched." if not errors else "; ".join(errors),
    }


@run_evaluator
def product_result_evaluator(run, example) -> dict[str, Any]:
    reference = example.outputs or {}
    expected_ids = reference.get("expected_product_ids")

    if expected_ids is None:
        return {
            "key": "product_result_accuracy",
            "value": "not_applicable",
            "comment": "No expected product IDs were defined for this example.",
        }

    actual_ids = (run.outputs or {}).get("product_ids", [])
    passed = actual_ids == expected_ids
    return {
        "key": "product_result_accuracy",
        "score": passed,
        "comment": f"Expected product IDs {expected_ids}; got {actual_ids}.",
    }


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    evaluation_api_key = os.getenv("LANGSMITH_EVAL_API_KEY", "").strip()
    if not evaluation_api_key:
        raise RuntimeError(
            "LANGSMITH_EVAL_API_KEY is missing from .env. "
            "Keep it separate from the tracing-only LANGSMITH_API_KEY."
        )

    # Import after environment loading so the project configuration is available.
    from app.graph_agent import graph

    client = Client(api_key=evaluation_api_key)
    dataset = client.read_dataset(dataset_name=DATASET_NAME)
    examples = list(client.list_examples(dataset_id=dataset.id))
    if not examples:
        raise RuntimeError(f"Dataset '{DATASET_NAME}' contains no examples.")

    print(f"Dataset: {DATASET_NAME}")
    print(f"Dataset examples: {len(examples)}")
    print("Starting LangSmith evaluation. Each example uses an isolated user/thread.")

    results = client.evaluate(
        build_target(graph),
        data=DATASET_NAME,
        evaluators=[
            tool_selection_evaluator,
            tool_argument_evaluator,
            product_result_evaluator,
        ],
        experiment_prefix="blink-ai-agent-eval-v1",
        description=(
            "Blink AI shopping assistant evaluation. Measures expected tool "
            "selection, tool argument accuracy, and product result accuracy."
        ),
        metadata={
            "project": "Blink AI Agentic Shopping Assistant",
            "evaluation_version": "v1",
            "dataset_name": DATASET_NAME,
        },
        max_concurrency=1,
        blocking=True,
        error_handling="log",
    )

    print("\nLangSmith evaluation completed.")
    print(results)
    print("Open LangSmith > Datasets & Experiments to inspect the experiment.")


if __name__ == "__main__":
    main()
