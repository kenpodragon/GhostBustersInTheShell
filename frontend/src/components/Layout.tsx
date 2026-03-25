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
        <div className="theme-switch" onClick={toggleTheme}>
          <span className={`theme-icon ${theme === 'light' ? 'theme-active' : ''}`}>&#9788;</span>
          <div className={`theme-track ${theme === 'light' ? 'theme-track-light' : ''}`}>
            <div className={`theme-thumb ${theme === 'light' ? 'theme-thumb-light' : ''}`} />
          </div>
          <span className={`theme-icon ${theme === 'dark' ? 'theme-active' : ''}`}>&#9790;</span>
        </div>
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
