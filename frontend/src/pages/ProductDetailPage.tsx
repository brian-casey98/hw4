import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, formatPrice, getProduct } from '../api.ts'
import type { ProductDetail } from '../types.ts'
import { usePageTitle } from '../usePageTitle.ts'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; product: ProductDetail }
  | { status: 'missing' }
  | { status: 'error' }

export function ProductDetailPage() {
  const { productId } = useParams()
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const title = state.status === 'ready' ? state.product.name : 'Product'
  usePageTitle(title)

  useEffect(() => {
    if (!productId) {
      setState({ status: 'missing' })
      return
    }
    let cancelled = false
    setState({ status: 'loading' })
    getProduct(productId)
      .then((product) => {
        if (!cancelled) setState({ status: 'ready', product })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 404) {
          setState({ status: 'missing' })
          return
        }
        setState({ status: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [productId])

  if (state.status === 'loading') {
    return (
      <section className="wrap page">
        <p className="status">Loading this piece…</p>
      </section>
    )
  }

  if (state.status === 'missing') {
    return (
      <section className="wrap page narrow">
        <h1>That piece is not in the catalogue</h1>
        <p>Check the product link, or go back to the full list.</p>
        <Link className="button" to="/products">
          All products
        </Link>
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section className="wrap page narrow">
        <h1>This piece did not load</h1>
        <p>Start the backend and refresh.</p>
        <Link className="button" to="/products">
          All products
        </Link>
      </section>
    )
  }

  const { product } = state
  const total = product.inventory.reduce((sum, row) => sum + row.quantity, 0)

  return (
    <section className="wrap page">
      <p className="back-link">
        <Link to="/products">All products</Link>
      </p>
      <article className="detail">
        <div className="detail-media">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-copy">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-description">{product.description}</p>
          {product.colors.length > 0 ? (
            <p className="color-list">Colors: {product.colors.join(', ')}</p>
          ) : null}
          <h2>Sizes</h2>
          <p className="stock-total">
            {total === 0 ? 'None available right now.' : `${total} available across all sizes.`}
          </p>
          <p className="color-note">Size counts are for this piece as a whole, not for one color.</p>
          {product.inventory.length === 0 ? (
            <p>No size counts are listed for this piece.</p>
          ) : (
            <ul className="sizes">
              {product.inventory.map((row) => (
                <li key={row.size}>
                  <span className="size-label">{row.size}</span>
                  {row.quantity === 0 ? (
                    <span className="stock stock-out">Out of stock</span>
                  ) : (
                    <span className={row.quantity <= 5 ? 'stock stock-low' : 'stock stock-in'}>
                      {row.quantity} in stock
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </article>
    </section>
  )
}
