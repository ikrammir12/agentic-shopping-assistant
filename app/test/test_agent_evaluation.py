
from tools.product_tools import (
    search_product_tool,
    compare_product_tool,
)


def test_search_respects_budget():
    """Every returned product must satisfy the requested budget."""

    results = search_product_tool.invoke({
        "category": "honey",
        "max_price": 20,
        "sort_by": "price_asc"
    })

    assert isinstance(results, list)

    for product in results:
        assert product["price"] <= 20, (
            f"Budget violation: {product['name']} costs "
            f"${product['price']}"
        )

    print("PASSED: Search respects the $20 budget")


def test_search_returns_correct_sort_order():
    """Products must be sorted by ascending price."""

    results = search_product_tool.invoke({
        "category": "honey",
        "max_price": 20,
        "sort_by": "price_asc"
    })

    prices = [product["price"] for product in results]

    assert prices == sorted(prices), (
        "Products are not sorted by ascending price"
    )

    print("PASSED: Search sorting is correct")


def test_comparison_calculations():
    """Highest rating and lowest price must be calculated correctly."""

    result = compare_product_tool.invoke({
        "product_name1": "Organic Raw Honey",
        "product_name2": "Wildflower Honey"
    })

    assert isinstance(result, dict)

    product1 = result["product_1"]
    product2 = result["product_2"]

    assert product1["avg_rating"] != product2["avg_rating"]
    assert product1["price"] != product2["price"]

    expected_highest_rated = (
        product1["name"]
        if product1["avg_rating"] > product2["avg_rating"]
        else product2["name"]
    )

    expected_lowest_price = (
        product1["name"]
        if product1["price"] < product2["price"]
        else product2["name"]
    )

    assert result["highest_rated"] == expected_highest_rated

    assert result["lowest_price"] == expected_lowest_price

    print("PASSED: Product comparison calculations are correct")


def test_unknown_category_returns_empty_list():
    """A nonexistent category should return no products."""

    results = search_product_tool.invoke({
        "category": "category_that_does_not_exist_12345",
        "max_price": None,
        "sort_by": "price_asc"
    })

    assert results == []

    print("PASSED: Unknown category returns an empty list")


def test_negative_budget_is_rejected():
    """Invalid budget must be rejected by input validation."""

    try:
        search_product_tool.invoke({
            "category": "honey",
            "max_price": -20,
            "sort_by": "price_asc"
        })

    except ValueError:
        print("PASSED: Negative budget was rejected")
        return

    raise AssertionError("Negative budget was unexpectedly accepted")


if __name__ == "__main__":

    tests = [
        test_search_respects_budget,
        test_search_returns_correct_sort_order,
        test_comparison_calculations,
        test_unknown_category_returns_empty_list,
        test_negative_budget_is_rejected,
    ]

    for test in tests:
        test()

    print("\nAll evaluation tests passed!")
