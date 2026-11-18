import { useEffect, useState } from 'react'
import {
  GitCompareArrows,
  Heart,
  LogOut,
  Menu,
  Plus,
  UserRound,
  X,
} from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { useFavorites } from '../../context/FavoritesContext.jsx'
import { resolveMediaUrl } from '../../api/client.js'
import { getCompareList } from '../../utils/compare.js'

const links = [
  { to: '/catalog', label: 'Каталог' },
  { to: '/about', label: 'О проекте' },
  { to: '/contacts', label: 'Контакты' },
]

export default function Header() {
  const { user, isAuthenticated, signOut } = useAuth()
  const { favorites } = useFavorites()
  const [menuOpen, setMenuOpen] = useState(false)
  const [compareCount, setCompareCount] = useState(() => getCompareList().length)
  const navigate = useNavigate()

  useEffect(() => {
    const update = () => setCompareCount(getCompareList().length)
    window.addEventListener('autokg:compare-updated', update)
    return () => window.removeEventListener('autokg:compare-updated', update)
  }, [])

  const logout = async () => {
    await signOut()
    setMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="header-inner container">
        <Link className="brand" to="/" aria-label="AutoKG — на главную">
          <span className="brand-name">Auto<span>KG</span></span>
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
            <NavLink
              key={link.to}
              to={link.to}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}
            >
              {link.label}
            </NavLink>
          ))}
          {isAuthenticated && user?.role === 'admin' && user?.is_staff && (
            <NavLink
              to="/admin"
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => (isActive ? 'nav-link nav-link--active' : 'nav-link')}
            >
              Админ-панель
            </NavLink>
          )}
          <NavLink
            to="/favorites"
            className={({ isActive }) => (isActive ? 'nav-link nav-link--active mobile-only' : 'nav-link mobile-only')}
            onClick={() => setMenuOpen(false)}
          >
            Избранное {favorites.length > 0 && <span className="nav-count">{favorites.length}</span>}
          </NavLink>
          {isAuthenticated && (
            <NavLink
              to="/dashboard"
              onClick={() => setMenuOpen(false)}
              className="nav-link mobile-only"
            >
              Личный кабинет
            </NavLink>
          )}
          {!isAuthenticated && (
            <>
              <NavLink to="/login" onClick={() => setMenuOpen(false)} className="nav-link mobile-only">
                Войти
              </NavLink>
              <NavLink to="/register" onClick={() => setMenuOpen(false)} className="nav-link mobile-only">
                Регистрация
              </NavLink>
            </>
          )}
          {isAuthenticated && (
            <button type="button" className="nav-link nav-logout mobile-only" onClick={logout}>
              <LogOut size={16} /> Выйти
            </button>
          )}
        </nav>

        <div className="header-actions">
          <Link className="header-favorite" to="/favorites" aria-label="Избранное">
            <Heart size={20} />
            {favorites.length > 0 && <span>{favorites.length}</span>}
          </Link>
          {compareCount > 0 && (
            <Link className="header-compare" to="/compare" aria-label="Сравнение">
              <GitCompareArrows size={20} />
              <span>{compareCount}</span>
            </Link>
          )}
          <Link
            className="button button--primary button--header"
            to={isAuthenticated ? '/cars/new' : '/login'}
          >
            <Plus size={17} />
            <span>Продать автомобиль</span>
          </Link>
          {isAuthenticated ? (
            <Link className="user-chip" to="/dashboard" aria-label="Личный кабинет">
              <span className="user-avatar">
                {user?.profile_photo
                  ? <img src={resolveMediaUrl(user.profile_photo)} alt={user?.first_name || 'Профиль'} />
                  : (user?.first_name || user?.email || 'A').slice(0, 1).toUpperCase()
                }
              </span>
              <span>{user?.first_name || 'Кабинет'}</span>
            </Link>
          ) : (
            <>
              <Link className="button button--outline button--header header-login" to="/login">
                <UserRound size={16} /><span>Войти</span>
              </Link>
              <Link className="button button--outline button--header header-register" to="/register">
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
