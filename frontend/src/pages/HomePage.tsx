import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProducts } from '../api.ts'
import { useCatalogue } from '../catalogue.tsx'
import { ProductCard } from '../components/ProductCard.tsx'
import type { Product } from '../types.ts'
import { usePageTitle } from '../usePageTitle.ts'

const featuredIds = [
  'basic-hoodie-big-yale',
  'boola-boola-t-shirt',
  'yale-dad-crewneck',
  '2025-yale-vs-harvard-t-shirt',
]

function pickFeatured(products: Product[]): Product[] {
  const chosen = featuredIds
    .map((id) => products.find((product) => product.product_id === id))
    .filter((product): product is Product => product !== undefined)
  if (chosen.length >= 4) return chosen.slice(0, 4)
  const rest = products.filter(
    (product) => !chosen.some((item) => item.product_id === product.product_id),
  )
  return [...chosen, ...rest].slice(0, 4)
}

export function HomePage() {
  usePageTitle('Campus Customs')
  const { matches, query, clearMatches } = useCatalogue()
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  const showingMatches = matches !== null && matches.length > 0
  const shelf = showingMatches ? matches : products

  useEffect(() => {
    let cancelled = false
    listProducts()
      .then((rows) => {
        if (!cancelled) setProducts(pickFeatured(rows))
      })
      .catch(() => {
        if (!cancelled) setError('The featured pieces did not load. Refresh the page in a moment.')
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
    <div className="home">
      <section className="hero">
        <div className="scene-photo" aria-hidden="true" />
        <div className="hero-shade" aria-hidden="true" />
        <div className="wrap hero-copy">
          <p className="eyebrow eyebrow-light">Yale Bulldog Blue</p>
          <h1>Yale apparel from the shop on Broadway.</h1>
          <p className="lede">
            Campus Customs is Yale Bulldog Blue: licensed hoodies, crewnecks,
            t-shirts, and jackets for the university, the residential colleges,
            the graduate schools, and the teams. The fleece and cotton are the
            same pieces the Broadway shop puts on the floor, ready to wear or to give.
          </p>
          <div className="hero-actions">
            <Link className="button" to="/products">
              Shop products
            </Link>
            <Link className="button button-ghost" to="/about">
              About the shop
            </Link>
          </div>
        </div>
      </section>

      <div className="store-sheet">
      <section className="wrap points">
        <article>
          <h2>Made to be worn</h2>
          <p>
            Heavy fleece, soft cotton, and cuts people live in, from an everyday hoodie
            to a game-day tee.
          </p>
        </article>
        <article>
          <h2>A wide Yale shelf</h2>
          <p>
            University lettering, residential-college crests, graduate-school marks,
            and team gear, in the colors the shop carries.
          </p>
        </article>
        <article>
          <h2>Find your size</h2>
          <p>
            Open a piece to see which sizes are on hand, then pick a hoodie, a gift,
            or a shirt you can take with you.
          </p>
        </article>
      </section>

      <section className="wrap shelf" id="catalogue-matches">
        <div className="section-head">
          <h2>{showingMatches ? 'Matching pieces' : 'A few to start with'}</h2>
          {showingMatches ? (
            <button className="text-button" type="button" onClick={clearMatches}>
              Show the featured pieces
            </button>
          ) : (
            <Link to="/products">See all products</Link>
          )}
        </div>
        {showingMatches ? <p className="match-note">From your question: {query}</p> : null}
        {error ? <p className="status">{error}</p> : null}
        <div className="product-grid">
          {shelf.map((product) => (
            <ProductCard key={product.product_id} product={product} titleTag="h3" />
          ))}
        </div>
      </section>
      </div>

      <section className="visit">
        <div className="scene-photo scene-photo-late" aria-hidden="true" />
        <div className="hero-shade" aria-hidden="true" />
        <div className="wrap visit-copy">
          <h2>Walk over if you are on campus</h2>
          <p>
            The shop is at 57 Broadway, New Haven, CT 06511. Shop the pieces here,
            or ask the shop assistant to help you find a college, a team, or a size.
          </p>
        </div>
      </section>
    </div>
  )
}
