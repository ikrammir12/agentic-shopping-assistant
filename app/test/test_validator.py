
from tools.product_tools import search_product_tool

# Test 1: Honey under $20
result = search_product_tool.invoke({
    "category": "honey",
    "max_price": 20,
    "sort_by": "price_asc"
})

for product in result:
    print(product["name"], product["price"])

# Test 2: Honey with no budget limit
result = search_product_tool.invoke({
    "category": "honey",
    "max_price": None,
    "sort_by": "price_desc"
})

print("\nDescending price:")
for product in result:
    print(product["name"], product["price"])
