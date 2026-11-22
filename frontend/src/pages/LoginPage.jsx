import { useState } from 'react'
import { ArrowLeft, ArrowRight, Building2, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { hasPanelAccess, homeForRole } from '../utils/roles.js'

export default function LoginPage() {
  const { signIn, verifyLoginCode, signOut } = useAuth()
  const { notify } = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // Второй шаг для администратора: код из Telegram
  const [challengeId, setChallengeId] = useState(null)
  const [code, setCode] = useState('')

  const enter = async (user) => {
    if (!hasPanelAccess(user)) {
      await signOut()
      setError('Вход доступен только менеджерам автосалонов и администратору.')
      return
    }
    notify('Вы вошли в AutoBuy.', 'success')
    const from = location.state?.from?.pathname
    const home = homeForRole(user)
    navigate(from && from.startsWith(home) ? from : home, { replace: true })
  }

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const result = await signIn(form)
      if (result.twoFactor) {
        setChallengeId(result.twoFactor.challengeId)
        setCode('')
        return
      }
      await enter(result)
    } catch (requestError) {
      const status = requestError.response?.status
      setError(
        status === 429
          ? 'Слишком много попыток входа. Подождите и попробуйте снова.'
          : status === 401
            ? 'Неверный email или пароль, либо аккаунт отключён.'
            : getErrorMessage(requestError, 'Не удалось войти. Проверьте данные.'),
      )
    } finally {
      setLoading(false)
    }
  }

  const submitCode = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await enter(await verifyLoginCode(challengeId, code))
    } catch (requestError) {
      const message = getErrorMessage(requestError, 'Не удалось проверить код.')
      setError(requestError.response?.status === 429 ? 'Слишком много попыток. Подождите минуту.' : message)
      if (/заново/i.test(message)) {
        setChallengeId(null)
        setCode('')
      }
    } finally {
      setLoading(false)
    }
  }

  const restart = () => {
    setChallengeId(null)
    setCode('')
    setError('')
  }

  return (
    <section className="auth-page">
      <div className="auth-card">
        <div className="auth-icon">{challengeId ? <ShieldCheck size={22} /> : <Building2 size={22} />}</div>
        <span className="eyebrow">{challengeId ? 'Подтверждение входа' : 'Для автосалонов'}</span>
        <h1>{challengeId ? 'Код из Telegram' : 'Вход в кабинет'}</h1>
        <p className="auth-intro">
          {challengeId
            ? 'Мы отправили 6-значный код в Telegram администратора. Он действует 5 минут.'
            : 'Размещать объявления на AutoBuy могут только автосалоны-партнёры. Аккаунт выдаёт администратор платформы.'}
        </p>
        {error && <div className="form-alert" role="alert">{error}</div>}
        {challengeId ? (
          <form className="form-stack" onSubmit={submitCode}>
            <label className="field-label">Код подтверждения<input type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required autoFocus value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" /></label>
            <button className="button button--primary button--wide" type="submit" disabled={loading || code.length !== 6}>{loading ? 'Проверяем…' : 'Подтвердить'} <ArrowRight size={17} /></button>
            <div className="form-inline-link"><button type="button" className="link-button" onClick={restart}>Войти заново / отправить новый код</button></div>
          </form>
        ) : (
          <form className="form-stack" onSubmit={submit}>
            <label className="field-label">Электронная почта<input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="manager@salon.kg" /></label>
            <label className="field-label">Пароль<span className="password-field"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Введите пароль" /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span></label>
            <div className="form-inline-link"><Link to="/password-reset">Забыли пароль?</Link></div>
            <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'Входим…' : 'Войти'} <ArrowRight size={17} /></button>
          </form>
        )}
        <Link className="button button--outline button--wide auth-home-button" to="/"><ArrowLeft size={17} /> На сайт</Link>
        <p className="auth-bottom">Хотите разместить свой автосалон? <Link to="/contacts">Свяжитесь с нами</Link></p>
      </div>
    </section>
  )
}
