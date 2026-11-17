import { useState } from 'react'
import { ArrowRight, Eye, EyeOff, LockKeyhole } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function LoginPage() {
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
      await signIn(form)
      notify('Вы вошли в AutoKG.', 'success')
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось войти. Проверьте данные.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <div className="auth-icon"><LockKeyhole size={22} /></div>
        <span className="eyebrow">С возвращением</span>
        <h1>Войдите в аккаунт</h1>
        <p className="auth-intro">Управляйте объявлениями и сохраняйте автомобили.</p>
        {error && <div className="form-alert" role="alert">{error}</div>}
        <form className="form-stack" onSubmit={submit}>
          <label className="field-label">Электронная почта<input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="name@example.com" /></label>
          <label className="field-label">Пароль<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Введите пароль" /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
          <div className="form-inline-link"><Link to="/password-reset">Забыли пароль?</Link></div>
          <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'Входим…' : 'Войти'} <ArrowRight size={17} /></button>
        </form>
        <p className="auth-bottom">Нет аккаунта? <Link to="/register">Зарегистрироваться</Link></p>
      </div>
    </section>
  )
}
