
import json
from uuid import uuid4

from pydantic import BaseModel, Field

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

import graph_agent
from llm import get_llm


# -----------------------------------------
# 1. Define the judge's required output
# -----------------------------------------

class EvaluationResult(BaseModel):

    budget_compliant: bool = Field(
        description="Whether every recommended product is within the user's budget."
    )

    source_supported: bool = Field(
        description="Whether factual product claims are supported by database results."
    )

    unsupported_claims: list[str] = Field(
        description="Factual claims that cannot be verified from the provided product data."
    )

    score: int = Field(
        ge=1,
        le=5,
        description="Overall answer quality score from 1 to 5."
    )

    reasoning: str = Field(
        description="Explanation for the evaluation."
    )


# -----------------------------------------
# 2. Configure the evaluation judge
# -----------------------------------------

judge_llm = get_llm().with_structured_output(
    EvaluationResult
)


def test_llm_answer_grounding():

    graph_agent.create_memory_table()

    unique_id = uuid4().hex

    user_id = f"judge-user-{unique_id}"

    config = {
        "recursion_limit": 20,
        "configurable": {
            "thread_id": f"judge-thread-{unique_id}",
            "user_id": user_id,
        },
    }

    user_request = "Find honey products under $20."

    # -------------------------------------
    # 3. Run the real shopping assistant
    # -------------------------------------

    with graph_agent.trace_context():

        with graph_agent.trace_span("judge_evaluation"):

            result = graph_agent.graph.invoke(
                {
                    "messages": [
                        HumanMessage(content=user_request)
                    ]
                },
                config,
            )

            messages = result["messages"]

            # Collect database tool results.
            tool_messages = [
                message
                for message in messages
                if isinstance(message, ToolMessage)
                and message.name == "search_product_tool"
            ]

            assert tool_messages, (
                "No product search results were received."
            )

            source_data = []

            for message in tool_messages:

                products = json.loads(message.content)

                assert isinstance(products, list)

                source_data.extend(products)

            assert source_data, "Database returned no products."

            # Find the final answer.
            final_message = next(
                (
                    message
                    for message in reversed(messages)
                    if isinstance(message, AIMessage)
                    and not getattr(message, "tool_calls", [])
                ),
                None,
            )

            assert final_message is not None

            final_answer = str(final_message.content)

            # -------------------------------------
            # 4. Prepare the judge's evaluation data
            # -------------------------------------

            evaluation_input = {
                "user_request": user_request,
                "trusted_product_data": source_data,
                "assistant_final_answer": final_answer,
            }

            system_prompt = """
            You are a strict evaluator of a shopping assistant.

            Evaluate the assistant's final answer using ONLY the
            supplied trusted product data.

            Evaluation rules:

            1. Check whether every recommended or listed product
               exists in the supplied product data.

            2. Check whether stated prices match the supplied data.

            3. Check whether every recommended product respects
               the customer's $20 budget.

            4. Do not accept unsupported claims about health benefits,
               quality, origin, taste, or other product attributes.

            5. Do not treat an assumption as a verified product fact.

            Scoring:

            5 = Fully supported and satisfies all constraints.
            4 = Correct with only minor presentation issues.
            3 = Some unsupported or unclear claims.
            2 = Significant factual or constraint violations.
            1 = Mostly incorrect or misleading.

            Be strict. Explain the evidence behind your judgment.
            """

            # -------------------------------------
            # 5. Ask the LLM to evaluate the answer
            # -------------------------------------

            with graph_agent.trace_span("llm.judge"):

                evaluation = judge_llm.invoke(
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(
                            content=json.dumps(
                                evaluation_input,
                                ensure_ascii=False,
                                indent=2,
                            )
                        ),
                    ]
                )

            # -------------------------------------
            # 6. Display the evaluation
            # -------------------------------------

            print("\n========== ORIGINAL ANSWER ==========")

            print(final_answer)

            print("\n========== JUDGE RESULTS ==========")

            print("Budget compliant:", evaluation.budget_compliant)

            print("Source supported:", evaluation.source_supported)

            print("Score:", evaluation.score, "/ 5")

            print("Unsupported claims:")

            for claim in evaluation.unsupported_claims:
                print("-", claim)

            print("\nReasoning:")
            print(evaluation.reasoning)

            # Report a result for human review.
            passed = (
                evaluation.budget_compliant
                and evaluation.source_supported
                and evaluation.score >= 4
                and not evaluation.unsupported_claims
            )

            print("\nJudge decision:", "PASS" if passed else "REVIEW")

            return evaluation


if __name__ == "__main__":

    test_llm_answer_grounding()

