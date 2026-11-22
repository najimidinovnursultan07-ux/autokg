import { useState } from 'react'
import { KeyRound, Mail, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { changeEmail, changePassword } from '../api/auth.js'
import { PageTitle } from '../components/common/States.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const initialForm = {
  current_password: '',
  new_password: '',
  new_password_confirmation: '',
}

const initialEmailForm = { new_email: '', current_password: '' }

// Смена email (логина) — только администратору платформы;
// менеджерам салонов email меняет администратор.
function EmailChangeForm() {
  const { user, setUser } = useAuth()
  const { notify } = useToast()
  const [form, setForm] = useState(initialEmailForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const updated = await changeEmail(form)
      setUser(updated)
      setForm(initialEmailForm)
      notify(`Email изменён. Теперь входите с ${updated.email}.`, 'success')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось изменить email.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="settings-form form-stack" onSubmit={submit}>
      <h2><Mail size={19} /> Email для входа</h2>
      <p className="settings-form-hint">Сейчас: <strong>{user?.email}</strong>. На старый адрес и в Telegram придёт уведомление о смене.</p>
      {error && <div className="form-alert" role="alert">{error}</div>}
      <label className="field-label">
        Новый email
        <input
          required
          type="email"
          autoComplete="email"
          placeholder="name@gmail.com"
          value={form.new_email}
          onChange={(event) => setForm({ ...form, new_email: event.target.value })}
        />
      </label>
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
      <button className="button button--primary" type="submit" disabled={loading}>
        <Mail size={17} /> {loading ? 'Сохраняем…' : 'Изменить email'}
      </button>
    </form>
  )
}

export default function AccountSettingsPage() {
  const { user, signOut } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const isAdmin = user?.role === 'admin'

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
        eyebrow={isAdmin ? 'Панель администратора' : 'Личный кабинет'}
        title="Настройки аккаунта"
        description="Защитите аккаунт и управляйте безопасностью входа."
      />
      <div className="settings-layout">
        <div className="settings-security-card">
          <span className="settings-security-icon"><ShieldCheck size={23} /></span>
          <h2>Безопасность аккаунта</h2>
          <p>
            Для любых изменений подтвердите текущий пароль. После смены пароля система завершит текущую сессию.
            {isAdmin && ' Вход в админку защищён кодом из Telegram.'}
          </p>
        </div>
        <div className="settings-forms">
          {isAdmin && <EmailChangeForm />}
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
                minLength={12}
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
                minLength={12}
                value={form.new_password_confirmation}
                onChange={(event) => setForm({ ...form, new_password_confirmation: event.target.value })}
              />
            </label>
            <button className="button button--primary" type="submit" disabled={loading}>
              <KeyRound size={17} /> {loading ? 'Сохраняем…' : 'Изменить пароль'}
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
