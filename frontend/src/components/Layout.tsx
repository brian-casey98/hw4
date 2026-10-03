import { Outlet } from 'react-router-dom'
import { ChatWidget } from './ChatWidget.tsx'
import { NavBar } from './NavBar.tsx'

export function Layout() {
  return (
    <div className="site">
      <NavBar />
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <p>Campus Customs · Yale Bulldog Blue</p>
        <p>57 Broadway, New Haven, CT 06511</p>
      </footer>
      <ChatWidget />
    </div>
  )
}
