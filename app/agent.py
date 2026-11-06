from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from llm import get_llm
from tools.product_tools import check_product_tool, search_product_tool, compare_product_tool

agent = create_agent(
    model = get_llm(),
    tools = [check_product_tool, search_product_tool, compare_product_tool],
system_prompt = """
You are a reliable AI shopping assistant.

RULES:

1. Always use tools to retrieve actual product information.
2. Use only information returned by the tools.
3. Never invent prices, ratings, reviews, ingredients,certifications, flavors, health benefits, or product features.
4. If information is unavailable in the database,explicitly say it is unavailable.
5. When comparing products, show:
   - Exact price
   - Average customer rating
   - Number of reviews
6. If there is a trade-off between price and rating,explain both options without forcing a winner.
7. Always generate a clear, customer-facing response.
"""
)

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Find honey products under $15 and show the cheapest first."
        }
    ]
})

final_message = result["messages"][-1]

print("\n========== FINAL MESSAGE DEBUG ==========")

print("Full Message:")
print(repr(final_message))

print("\nContent:")
print(repr(final_message.content))

print("\nTool Calls:")
print(final_message.tool_calls)

print("\nAdditional Arguments:")
print(final_message.additional_kwargs)

print("\nResponse Metadata:")
print(final_message.response_metadata)

print("\nUsage Metadata:")
print(final_message.usage_metadata)


llm = get_llm()

test_response = llm.invoke(
    "Reply with exactly one sentence: Hello, how can I help you?"
)

print("LLM Test:", repr(test_response.content))
print("Metadata:", test_response.response_metadata)