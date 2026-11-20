import { useEffect, useState } from 'react'
import { Building2, GitCompareArrows, LogOut, Menu, Plus, X } from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { getCompareList } from '../../utils/compare.js'

const links = [
  { to: '/catalog', label: 'Каталог' },
  { to: '/dealers', label: 'Салоны' },
  { to: '/about', label: 'О проекте' },
  { to: '/contacts', label: 'Контакты' },
]

const navClass = (extra = '') => ({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''} ${extra}`

export default function Header() {
  const { user, isAuthenticated, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [compareCount, setCompareCount] = useState(() => getCompareList().length)
  const navigate = useNavigate()
  const isDealer = isAuthenticated && user?.role === 'dealer'

  useEffect(() => {
    const update = () => setCompareCount(getCompareList().length)
    window.addEventListener('autobuy:compare-updated', update)
    return () => window.removeEventListener('autobuy:compare-updated', update)
  }, [])

  const close = () => setMenuOpen(false)
  const logout = async () => {
    await signOut()
    close()
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="header-inner container">
        <Link className="brand" to="/" aria-label="AutoBuy — на главную">
          <span className="brand-name">Auto<span>Buy</span></span>
        </Link>

        <button
          type="button"
          className="icon-button mobile-menu-toggle"
          aria-label={menuOpen ? 'Закрыть меню' : 'Открыть меню'}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={21} /> : <Menu size={21} />}
        </button>

        <nav className={`main-nav ${menuOpen ? 'main-nav--open' : ''}`}>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} onClick={close} className={navClass()}>{link.label}</NavLink>
          ))}
          {/* Ссылку на админку на публичном сайте не показываем — админ заходит по /admin */}
          {isDealer && (
            <NavLink to="/dashboard" end onClick={close} className={navClass('mobile-only')}>Кабинет салона</NavLink>
          )}
          {isDealer && (
            <NavLink to="/dashboard/cars/new" onClick={close} className={navClass('mobile-only')}><Plus size={16} /> Добавить авто</NavLink>
          )}
          {isDealer && (
            <button type="button" className="nav-link nav-logout mobile-only" onClick={logout}><LogOut size={16} /> Выйти</button>
          )}
        </nav>

        <div className="header-actions">
          {compareCount > 0 && (
            <Link className="header-compare" to="/compare" aria-label="Сравнение">
              <GitCompareArrows size={20} />
              <span>{compareCount}</span>
            </Link>
          )}
          {isDealer && (
            <Link className="button button--primary button--header" to="/dashboard/cars/new">
              <Plus size={17} /><span>Добавить авто</span>
            </Link>
          )}
          {/* Гостям кнопки входа не показываем: салоны входят по прямой ссылке /login */}
          {isDealer && (
            <Link className="user-chip" to="/dashboard" aria-label="Кабинет салона">
              <span className="user-avatar"><Building2 size={15} /></span>
              <span>{user?.dealer_name || 'Кабинет'}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
