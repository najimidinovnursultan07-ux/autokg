import { useState } from 'react'
import { ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function AdminLoginPage() {
  const { signIn } = useAuth()
  const { notify } = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const user = await signIn(form)
      if (user?.role !== 'admin' || user?.is_staff !== true) {
        setError('У вас нет прав администратора.')
        return
      }
      notify('Добро пожаловать в панель администратора.', 'success')
      const from = location.state?.from?.pathname
      navigate(from && from.startsWith('/admin') ? from : '/admin', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Неверный email или пароль.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="admin-login-page">
      <div className="admin-login-card">
        <div className="admin-login-header">
          <span className="admin-login-icon"><ShieldCheck size={28} /></span>
          <h1>AutoKG Admin</h1>
          <p>Панель администратора</p>
        </div>

        {error && <div className="form-alert" role="alert">{error}</div>}

        <form className="form-stack" onSubmit={submit}>
          <label className="field-label">
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="admin@example.com"
            />
          </label>
          <label className="field-label">
            Пароль
            <span className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Введите пароль"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
          </label>
          <button
            className="button button--primary button--wide"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Входим…' : 'Войти в панель'} <ArrowRight size={17} />
          </button>
        </form>
      </div>
    </section>
  )
}
