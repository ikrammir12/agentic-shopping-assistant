
import type { ChatProduct } from '../services/chat'

type ProductCardProps = {
  product: ChatProduct & {
    average_rating?: number | null
    review_count?: number | null
  }
}

function ProductCard({ product }: ProductCardProps) {

  const isOrganic = product.is_organic === 1

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-violet-300">

      {/* Product heading */}
      <div className="flex items-start justify-between gap-3">

        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900">
            {product.name}
          </h3>

          <p className="mt-1 text-xs capitalize text-slate-500">
            {product.category}
          </p>
        </div>

        <span className="shrink-0 rounded-lg bg-violet-50 px-3 py-1.5 text-sm font-bold text-violet-700">
          ${product.price.toFixed(2)}
        </span>

      </div>

      {/* Description */}
      <p className="mt-3 text-sm leading-6 text-slate-600">
        {product.description}
      </p>

      {/* Product attributes */}
      <div className="mt-4 flex flex-wrap items-center gap-2">

        {product.is_organic !== undefined && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              isOrganic
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {isOrganic ? 'Organic' : 'Not marked organic'}
          </span>
        )}

        {typeof product.average_rating === 'number' && (
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
            ★ {product.average_rating.toFixed(1)}
            {typeof product.review_count === 'number' &&
              ` (${product.review_count} reviews)`}
          </span>
        )}

      </div>

    </article>
  )
}

export default ProductCard
