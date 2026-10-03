import { Link } from 'react-router-dom'
import { usePageTitle } from '../usePageTitle.ts'

export function NotFoundPage() {
  usePageTitle('Page not found')

  return (
    <section className="wrap page narrow">
      <h1>That page is not on the shop</h1>
      <p>Use the menu to get back to the catalogue.</p>
      <Link className="button" to="/">
        Home
      </Link>
    </section>
  )
}
