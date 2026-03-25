import { useState, useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'

function Layout() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('ghostbusters-theme') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('ghostbusters-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <img src="/ghosted-guild.jpg" alt="Ghosted Guild" className="sidebar-icon" />
          <a href="https://discord.gg/Y8UxRmaAXw" target="_blank" rel="noopener noreferrer" className="sidebar-title-link">
            GhostBusters<br />In The Shell_
          </a>
        </div>
        <ul className="sidebar-nav">
          <li>
            <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
              [0] Scanner
            </NavLink>
          </li>
          <li>
            <NavLink to="/voice-profiles" className={({ isActive }) => isActive ? 'active' : ''}>
              [1] Voice Profiles
            </NavLink>
          </li>
        </ul>
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === 'dark' ? '[ LIGHT MODE ]' : '[ DARK MODE ]'}
        </button>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
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
