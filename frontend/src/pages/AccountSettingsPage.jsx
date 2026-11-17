import { useState } from 'react'
import { KeyRound, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../api/auth.js'
import { PageTitle } from '../components/common/States.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const initialForm = {
  current_password: '',
  new_password: '',
  new_password_confirmation: '',
}

export default function AccountSettingsPage() {
  const { signOut } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await changePassword(form)
      setForm(initialForm)
      await signOut()
      notify('Пароль изменён. Войдите снова с новым паролем.', 'success')
      navigate('/login', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось изменить пароль.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Личный кабинет"
        title="Настройки аккаунта"
        description="Защитите аккаунт и управляйте безопасностью входа."
      />
      <div className="settings-layout">
        <div className="settings-security-card">
          <span className="settings-security-icon"><ShieldCheck size={23} /></span>
          <h2>Безопасность аккаунта</h2>
          <p>Для смены пароля подтвердите текущий пароль. После сохранения система завершит текущую сессию.</p>
        </div>
        <form className="settings-form form-stack" onSubmit={submit}>
          <h2><KeyRound size={19} /> Изменение пароля</h2>
          {error && <div className="form-alert" role="alert">{error}</div>}
          <label className="field-label">
            Текущий пароль
            <input
              required
              type="password"
              autoComplete="current-password"
              value={form.current_password}
              onChange={(event) => setForm({ ...form, current_password: event.target.value })}
            />
          </label>
          <label className="field-label">
            Новый пароль
            <input
              required
              type="password"
              autoComplete="new-password"
              value={form.new_password}
              onChange={(event) => setForm({ ...form, new_password: event.target.value })}
            />
          </label>
          <label className="field-label">
            Повторите новый пароль
            <input
              required
              type="password"
              autoComplete="new-password"
              value={form.new_password_confirmation}
              onChange={(event) => setForm({ ...form, new_password_confirmation: event.target.value })}
            />
          </label>
          <button className="button button--primary" type="submit" disabled={loading}>
            <KeyRound size={17} /> {loading ? 'Сохраняем…' : 'Изменить пароль'}
          </button>
        </form>
      </div>
    </section>
  )
}
