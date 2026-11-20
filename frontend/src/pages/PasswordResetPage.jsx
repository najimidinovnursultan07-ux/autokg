import { useState } from 'react'
import { ArrowLeft, KeyRound, MailCheck } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset, requestPasswordReset } from '../api/auth.js'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function PasswordResetPage() {
  const [params] = useSearchParams()
  const uid = params.get('uid')
  const token = params.get('token')
  const isConfirm = Boolean(uid && token)
  const { notify } = useToast()
  const [email, setEmail] = useState('')
  const [form, setForm] = useState({ new_password: '', new_password_confirmation: '' })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (isConfirm) {
        await confirmPasswordReset({ uid, token, ...form })
        setMessage('Пароль изменён. Теперь войдите с новым паролем.')
        notify('Пароль успешно изменён.', 'success')
      } else {
        const response = await requestPasswordReset(email)
        setMessage(response.detail)
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось выполнить запрос.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <div className="auth-icon">{message ? <MailCheck size={22} /> : <KeyRound size={22} />}</div>
        <span className="eyebrow">Безопасность аккаунта</span>
        <h1>{isConfirm ? 'Новый пароль' : 'Восстановление пароля'}</h1>
        <p className="auth-intro">{isConfirm ? 'Создайте новый пароль для входа в AutoBuy.' : 'Укажите электронную почту — отправим инструкции, если аккаунт существует.'}</p>
        {message ? <div className="success-panel">{message}</div> : (
          <form className="form-stack" onSubmit={submit}>
            {error && <div className="form-alert" role="alert">{error}</div>}
            {isConfirm ? (
              <>
                <label className="field-label">Новый пароль<input type="password" minLength={12} required autoComplete="new-password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} /></label>
                <label className="field-label">Повторите пароль<input type="password" minLength={12} required autoComplete="new-password" value={form.new_password_confirmation} onChange={(e) => setForm({ ...form, new_password_confirmation: e.target.value })} /></label>
              </>
            ) : (
              <label className="field-label">Электронная почта<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" /></label>
            )}
            <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'Отправляем…' : isConfirm ? 'Сохранить новый пароль' : 'Отправить инструкции'}</button>
          </form>
        )}
        <Link className="auth-back" to="/login"><ArrowLeft size={16} /> Вернуться ко входу</Link>
      </div>
    </section>
  )
}
