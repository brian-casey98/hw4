import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth.tsx'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: true },
]

function itemClass(isActive: boolean): string {
  return isActive ? 'nav-link is-active' : 'nav-link'
}

export function NavBar() {
  const { user, ready, logout } = useAuth()

  return (
    <header className="site-header">
      <p className="announcement">Licensed Yale gear from Campus Customs</p>
      <nav className="nav" aria-label="Main">
        <NavLink className="brand" to="/" end>
          <span className="brand-badge" aria-hidden="true">
            CC
          </span>
          <span className="brand-words">
            <span className="brand-mark">Campus Customs</span>
            <span className="brand-sub">Yale Bulldog Blue</span>
          </span>
        </NavLink>
        <div className="nav-links">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => itemClass(isActive)}
            >
              {link.label}
            </NavLink>
          ))}
          {ready && user ? (
            <>
              <span className="nav-user">{user.first_name}</span>
              <button className="nav-button" type="button" onClick={() => void logout()}>
                Log out
              </button>
            </>
          ) : null}
          {ready && !user ? (
            <>
              <NavLink to="/login" className={({ isActive }) => itemClass(isActive)}>
                Log in
              </NavLink>
              <NavLink
                to="/create-account"
                className={({ isActive }) => (isActive ? 'nav-account is-active' : 'nav-account')}
              >
                Create Account
              </NavLink>
            </>
          ) : null}
        </div>
      </nav>
    </header>
  )
}
