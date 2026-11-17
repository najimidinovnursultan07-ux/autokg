import { BarChart3, CarFront, ExternalLink, LayoutDashboard, LogOut, MapPinned, Users } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'

const navigation = [
  { to: '/admin', label: 'Обзор', icon: LayoutDashboard, end: true },
  { to: '/admin/users', label: 'Пользователи', icon: Users },
  { to: '/admin/cars', label: 'Объявления', icon: CarFront },
  { to: '/admin/catalog', label: 'Справочники', icon: MapPinned },
]

export default function AdminLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const logout = async () => {
    await signOut()
    navigate('/', { replace: true })
  }

  return (
    <div className="container admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <span className="admin-brand-mark"><BarChart3 size={19} /></span>
          <span><strong>AutoKG</strong><small>Панель администратора</small></span>
        </div>
        <nav className="admin-navigation" aria-label="Административная панель">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              to={to}
              key={to}
              end={end}
              className={({ isActive }) => `admin-nav-link ${isActive ? 'admin-nav-link--active' : ''}`}
            >
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <span className="admin-signed-in">{user?.email}</span>
          <NavLink className="admin-nav-link" to="/"><ExternalLink size={17} /><span>На сайт</span></NavLink>
          <button type="button" className="admin-nav-link admin-logout" onClick={logout}>
            <LogOut size={17} /><span>Выйти</span>
          </button>
        </div>
      </aside>
      <main className="admin-main"><Outlet /></main>
    </div>
  )
}
