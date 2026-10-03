import { Link } from 'react-router-dom'
import { usePageTitle } from '../usePageTitle.ts'

export function AboutPage() {
  usePageTitle('About Us')

  return (
    <section className="wrap page narrow prose">
      <h1>About Us</h1>
      <p>
        Yale Bulldog Blue is the Campus Customs shop for licensed Yale apparel
        and accessories. The selection runs from everyday hoodies and crewnecks
        to residential-college crests, graduate-school marks, team wordmarks,
        and the oversized Yale lettering people wear around campus.
      </p>
      <p>
        Campus Clothing Company runs the storefront at 57 Broadway in New Haven.
        This website reads that shop's catalogue: the photo, the price, and the
        size counts are the ones stored with each product, so a question about
        what is left in a size can be answered from the same records the page uses.
      </p>
      <p>
        If you are nearby, the Broadway store is still the place to see a fabric
        in person. Online, browse the products or open the chat in the corner
        when you want help choosing a college, a team, or a fit.
      </p>
      <p>
        <Link className="button" to="/products">
          Browse the catalogue
        </Link>
      </p>
    </section>
  )
}
