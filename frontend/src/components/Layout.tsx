import { Outlet, NavLink } from 'react-router-dom'

function Layout() {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-logo">
          {'>'} GhostBusters<br />
          {'  '}In The Shell_
        </div>
        <ul className="sidebar-nav">
          <li>
            <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
              [0] Analyze
            </NavLink>
          </li>
          <li>
            <NavLink to="/documents" className={({ isActive }) => isActive ? 'active' : ''}>
              [1] Documents
            </NavLink>
          </li>
          <li>
            <NavLink to="/voice-profiles" className={({ isActive }) => isActive ? 'active' : ''}>
              [2] Voice Profiles
            </NavLink>
          </li>
        </ul>
        <div style={{ marginTop: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          v0.1.0 // local instance
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
