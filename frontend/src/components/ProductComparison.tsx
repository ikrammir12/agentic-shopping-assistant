
export type ComparedProduct = {
  id?: number
  name: string
  price: number
  avg_rating: number | null
  review_count: number
}

export type ProductComparisonData = {
  product_1: ComparedProduct
  product_2: ComparedProduct
  highest_rated: string | null
  lowest_price: string | null
  recommended_product: string | null
  reason: string
}

type ProductComparisonProps = {
  comparison: ProductComparisonData
}

function formatPrice(price: number) {
  return `$${price.toFixed(2)}`
}

function ProductComparison({
  comparison,
}: ProductComparisonProps) {

  const first = comparison.product_1
  const second = comparison.product_2

  const priceDifference = Math.abs(first.price - second.price)

  const cheaperProduct =
    first.price < second.price
      ? first.name
      : second.price < first.price
        ? second.name
        : null

  function renderProduct(product: ComparedProduct) {

    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4">

        <h3 className="font-semibold text-slate-900">
          {product.name}
        </h3>

        <div className="mt-4">
          <p className="text-xs text-slate-500">
            Price
          </p>

          <p className="text-2xl font-bold text-violet-700">
            {formatPrice(product.price)}
          </p>
        </div>

        <div className="mt-4">
          <p className="text-xs text-slate-500">
            Average customer rating
          </p>

          {product.avg_rating !== null ? (
            <p className="font-semibold text-amber-600">
              ★ {product.avg_rating.toFixed(2)} / 5
            </p>
          ) : (
            <p className="text-sm text-slate-500">
              No ratings available
            </p>
          )}
        </div>

        <div className="mt-4">
          <p className="text-xs text-slate-500">
            Customer reviews
          </p>

          <p className="text-sm font-medium text-slate-700">
            {product.review_count}
          </p>
        </div>

        {cheaperProduct === product.name && (
          <span className="mt-4 inline-block rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            Lower price
          </span>
        )}

      </div>
    )
  }

  return (
    <section className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-5">

      {/* Header */}
      <div className="mb-5">
        <h3 className="text-lg font-bold text-slate-900">
          Product Comparison
        </h3>

        <p className="text-sm text-slate-500">
          Side-by-side comparison based on database information
        </p>
      </div>

      {/* Product comparison */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">

        {renderProduct(first)}
        {renderProduct(second)}

      </div>

      {/* Price difference */}
      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">

        <h4 className="text-sm font-semibold text-slate-800">
          Price Difference
        </h4>

        <p className="mt-2 text-sm text-slate-600">

          {priceDifference === 0
            ? 'Both products have the same price.'
            : `${cheaperProduct} is ${formatPrice(priceDifference)} cheaper.`}

        </p>

        <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
          <span>Lowest price</span>
          <span className="font-medium text-slate-700">
            {comparison.lowest_price ?? 'Not available'}
          </span>
        </div>

        <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
          <span>Highest rating</span>
          <span className="font-medium text-slate-700">
            {comparison.highest_rated ?? 'Not available'}
          </span>
        </div>

      </div>

      {/* AI recommendation */}
      <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50 p-4">

        <div className="flex items-center gap-2">
          <span className="text-lg">✦</span>

          <h4 className="font-semibold text-violet-900">
            AI Recommendation
          </h4>
        </div>

        <p className="mt-3 font-semibold text-violet-900">
          {comparison.recommended_product
            ? comparison.recommended_product
            : 'No clear winner'}
        </p>

        <p className="mt-2 text-sm leading-6 text-violet-800">
          {comparison.reason}
        </p>

      </div>

    </section>
  )
}

export default ProductComparison
