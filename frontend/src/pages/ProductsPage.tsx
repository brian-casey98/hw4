import { useEffect, useState } from 'react'
import { listProducts } from '../api.ts'
import { useCatalogue } from '../catalogue.tsx'
import { ProductCard } from '../components/ProductCard.tsx'
import type { Product } from '../types.ts'
import { usePageTitle } from '../usePageTitle.ts'

function filterProducts(products: Product[], search: string): Product[] {
  const tokens = search
    .toLowerCase()
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
  if (tokens.length === 0) return products
  return products.filter((product) => {
    const haystack = [
      product.name,
      product.garment_type,
      product.description,
      product.colors.join(' '),
      product.search_tags.join(' '),
    ]
      .join(' ')
      .toLowerCase()
    return tokens.every((token) => haystack.includes(token))
  })
}

export function ProductsPage() {
  usePageTitle('Products')
  const { matches, query, clearMatches } = useCatalogue()
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const showingMatches = matches !== null && matches.length > 0 && search.trim() === ''
  const shelf = filterProducts(showingMatches ? matches : products, search)

  useEffect(() => {
    let cancelled = false
    listProducts()
      .then((rows) => {
        if (!cancelled) setProducts(rows)
      })
      .catch(() => {
        if (!cancelled) {
          setError('The catalogue did not load. Start the backend and refresh.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!showingMatches) return
    document.getElementById('catalogue-matches')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [showingMatches, matches])

  return (
    <section className="wrap page" id="catalogue-matches">
      <header className="page-intro">
        <h1>{search.trim() ? 'Search results' : showingMatches ? 'Matching pieces' : 'Products'}</h1>
        <form className="catalogue-search" role="search" onSubmit={(event) => event.preventDefault()}>
          <label htmlFor="catalogue-search">Search the catalogue</label>
          <input
            id="catalogue-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Hoodie, crewneck, college, team"
            autoComplete="off"
          />
        </form>
        {showingMatches ? (
          <p>From your question: {query}</p>
        ) : (
          <p>
            The Campus Customs catalogue: Yale hoodies, crewnecks, tees, and
            jackets, with the shop photo, price, and a short description on each card.
          </p>
        )}
        {showingMatches ? (
          <button className="text-button" type="button" onClick={clearMatches}>
            Show the full catalogue
          </button>
        ) : null}
        {!loading && !error ? (
          <p className="count">{shelf.length} pieces</p>
        ) : null}
      </header>
      {loading ? <p className="status">Loading the catalogue…</p> : null}
      {error ? <p className="status">{error}</p> : null}
      {!loading && !error && shelf.length === 0 ? (
        <p className="status">No pieces match that search.</p>
      ) : null}
      <div className="product-grid">
        {shelf.map((product) => (
          <ProductCard key={product.product_id} product={product} />
        ))}
      </div>
    </section>
  )
}
