import { useState } from 'react'
import { BellRing } from 'lucide-react'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

/**
 * Кнопка подписки через Telegram-бота: создаёт подписку на сервере
 * и открывает бота по ссылке с одноразовым токеном (там нужно нажать «Старт»).
 */
export default function TelegramAlertButton({ request, label, className = '', title }) {
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)

  const subscribe = async () => {
    if (busy) return
    setBusy(true)
    // Вкладку открываем сразу по клику — иначе браузер заблокирует её как всплывающее окно
    const tab = window.open('', '_blank')
    try {
      const { bot_url: url } = await request()
      if (tab) {
        tab.opener = null
        tab.location.href = url
      } else {
        window.location.href = url
      }
      notify('Откройте бота в Telegram и нажмите «Старт» — подписка заработает.', 'success')
    } catch (error) {
      tab?.close()
      notify(getErrorMessage(error, 'Не удалось оформить подписку. Попробуйте позже.'), 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <button type="button" className={`button button--outline telegram-alert-btn ${className}`} onClick={subscribe} disabled={busy} title={title}>
      <BellRing size={16} />
      {busy ? 'Открываем Telegram…' : label}
    </button>
  )
}
