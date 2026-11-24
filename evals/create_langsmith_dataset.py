"""Create or complete Blink AI's LangSmith evaluation dataset from JSONL."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "evals" / "datasets" / "shopping_agent_v1.jsonl"
DATASET_NAME = "blink-ai-shopping-v1"


def load_cases() -> list[dict[str, Any]]:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {DATASET_PATH}")

    cases: list[dict[str, Any]] = []
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

            if not isinstance(case, dict):
                raise ValueError(f"Line {line_number} must contain a JSON object.")
            if not isinstance(case.get("inputs"), dict):
                raise ValueError(f"Line {line_number} is missing an 'inputs' object.")
            if not isinstance(case.get("outputs"), dict):
                raise ValueError(f"Line {line_number} is missing an 'outputs' object.")
            cases.append(case)

    if not cases:
        raise ValueError("The JSONL file contains no evaluation cases.")

    case_ids = [case.get("metadata", {}).get("case_id") for case in cases]
    if any(not case_id for case_id in case_ids):
        raise ValueError("Every dataset case must have metadata.case_id.")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate metadata.case_id values found in JSONL.")

    return cases


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    # Keep the tracing-only key separate from the key used to manage datasets.
    eval_api_key = os.getenv("LANGSMITH_EVAL_API_KEY", "").strip()
    if not eval_api_key:
        raise RuntimeError(
            "LANGSMITH_EVAL_API_KEY is missing. Add a LangSmith Personal Access "
            "Token (PAT) or appropriately permissioned Service Key to .env. "
            "Do not replace the existing LANGSMITH_API_KEY used for tracing."
        )

    cases = load_cases()
    client = Client(api_key=eval_api_key)

    if client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Found existing dataset: {DATASET_NAME}")
    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=(
                "Blink AI shopping assistant evaluation dataset. "
                "Contains expected tool selections, tool arguments, and result checks."
            ),
            metadata={
                "project": "Blink AI Agentic Shopping Assistant",
                "dataset_version": "v1",
                "source_file": "evals/datasets/shopping_agent_v1.jsonl",
            },
        )
        print(f"Created dataset: {DATASET_NAME}")

    existing_examples = list(client.list_examples(dataset_id=dataset.id))
    existing_case_ids = {
        example.metadata.get("case_id")
        for example in existing_examples
        if isinstance(example.metadata, dict)
    }

    created_count = 0
    skipped_count = 0

    for case in cases:
        metadata = case.get("metadata", {})
        case_id = metadata["case_id"]

        if case_id in existing_case_ids:
            skipped_count += 1
            continue

        # create_example is compatible with the project's LangSmith SDK version.
        client.create_example(
            inputs=case["inputs"],
            reference_outputs=case["outputs"],
            metadata=metadata,
            dataset_id=dataset.id,
        )
        created_count += 1

    final_examples = list(client.list_examples(dataset_id=dataset.id))
    print("\nLangSmith dataset sync completed.")
    print(f"Dataset name: {DATASET_NAME}")
    print(f"Dataset ID: {dataset.id}")
    print(f"Examples in dataset: {len(final_examples)}")
    print(f"New examples uploaded: {created_count}")
    print(f"Existing examples skipped: {skipped_count}")
    print("Open LangSmith > Datasets & Experiments to inspect the examples.")


if __name__ == "__main__":
    main()
