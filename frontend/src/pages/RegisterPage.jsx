import { useState } from 'react'
import { ArrowRight, UserRoundPlus } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const initialForm = {
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  password: '',
  password_confirmation: '',
}

export default function RegisterPage() {
  const { signUp } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const update = (key) => (event) => setForm((value) => ({ ...value, [key]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await signUp(form)
      notify('Аккаунт создан. Добро пожаловать в AutoKG!', 'success')
      navigate('/dashboard', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Проверьте введённые данные.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card auth-card--wide">
        <div className="auth-icon"><UserRoundPlus size={22} /></div>
        <span className="eyebrow">Присоединяйтесь к AutoKG</span>
        <h1>Создать аккаунт</h1>
        <p className="auth-intro">Один аккаунт для покупки и продажи автомобилей.</p>
        {error && <div className="form-alert" role="alert">{error}</div>}
        <form className="form-stack" onSubmit={submit}>
          <div className="field-grid">
            <label className="field-label">Имя<input required autoComplete="given-name" value={form.first_name} onChange={update('first_name')} /></label>
            <label className="field-label">Фамилия<input required autoComplete="family-name" value={form.last_name} onChange={update('last_name')} /></label>
          </div>
          <label className="field-label">Телефон<input required type="tel" autoComplete="tel" placeholder="+996700123456" value={form.phone} onChange={update('phone')} /></label>
          <label className="field-label">Электронная почта<input required type="email" autoComplete="email" placeholder="name@example.com" value={form.email} onChange={update('email')} /></label>
          <div className="field-grid">
            <label className="field-label">Пароль<input required type="password" autoComplete="new-password" minLength={12} value={form.password} onChange={update('password')} /></label>
            <label className="field-label">Повторите пароль<input required type="password" autoComplete="new-password" minLength={12} value={form.password_confirmation} onChange={update('password_confirmation')} /></label>
          </div>
          <p className="field-hint">Минимум 12 символов. Используйте буквы, цифры и знаки.</p>
          <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'Создаём аккаунт…' : 'Зарегистрироваться'} <ArrowRight size={17} /></button>
        </form>
        <p className="auth-bottom">Уже есть аккаунт? <Link to="/login">Войти</Link></p>
      </div>
    </section>
  )
}
