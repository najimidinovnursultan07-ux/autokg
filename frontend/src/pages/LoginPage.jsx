import { useState } from 'react'
import { ArrowRight, Building2, Eye, EyeOff } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { hasPanelAccess, homeForRole } from '../utils/roles.js'

export default function LoginPage() {
  const { signIn, signOut } = useAuth()
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
      if (!hasPanelAccess(user)) {
        await signOut()
        setError('Вход доступен только менеджерам автосалонов и администратору.')
        return
      }
      notify('Вы вошли в AutoBuy.', 'success')
      const from = location.state?.from?.pathname
      const home = homeForRole(user)
      navigate(from && from.startsWith(home) ? from : home, { replace: true })
    } catch (requestError) {
      const status = requestError.response?.status
      setError(
        status === 429
          ? 'Слишком много попыток входа. Подождите минуту и попробуйте снова.'
          : status === 401
            ? 'Неверный email или пароль, либо аккаунт отключён.'
            : getErrorMessage(requestError, 'Не удалось войти. Проверьте данные.'),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <div className="auth-icon"><Building2 size={22} /></div>
        <span className="eyebrow">Для автосалонов</span>
        <h1>Вход в кабинет</h1>
        <p className="auth-intro">
          Размещать объявления на AutoBuy могут только автосалоны-партнёры.
          Аккаунт выдаёт администратор платформы.
        </p>
        {error && <div className="form-alert" role="alert">{error}</div>}
        <form className="form-stack" onSubmit={submit}>
          <label className="field-label">Электронная почта<input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="manager@salon.kg" /></label>
          <label className="field-label">Пароль<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Введите пароль" /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
          <div className="form-inline-link"><Link to="/password-reset">Забыли пароль?</Link></div>
          <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'Входим…' : 'Войти'} <ArrowRight size={17} /></button>
        </form>
        <p className="auth-bottom">Хотите разместить свой автосалон? <Link to="/contacts">Свяжитесь с нами</Link></p>
      </div>
    </section>
  )
}
