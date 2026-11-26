import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, MessageCircle, SendHorizontal, Sparkles, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { adClickUrl, trackAdImpression } from '../../api/ads.js'
import { askAssistant } from '../../api/assistant.js'
import { resolveMediaUrl } from '../../api/client.js'
import { getErrorMessage } from '../../utils/errors.js'
import { formatPrice } from '../../utils/format.js'
import { SUPPORT_PHONE, whatsappLink } from '../../utils/contacts.js'

// В кабинетах и на служебных страницах помощник не нужен.
// На странице машины у покупателя свои кнопки связи с салоном — там тоже прячем.
const HIDDEN_PREFIXES = ['/cars/', '/dashboard', '/admin', '/payment', '/login', '/password-reset']
const STORAGE_KEY = 'autobuy:assistant'
const MAX_HISTORY = 16

const SUGGESTIONS = [
  'Подбери кроссовер до 2 000 000 сом',
  'Какие авто можно купить по мурабахе?',
  'Как связаться с продавцом?',
]

const GREETING = 'Здравствуйте! Я ИИ-помощник AutoBuy. Помогу подобрать автомобиль, расскажу о мурабахе и о том, как работает сайт.'

function loadHistory() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

function saveHistory(messages) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_HISTORY)))
  } catch {
    // приватный режим или запрет хранилища — история просто не сохранится
  }
}

// Модель иногда всё же присылает **жирный** — убираем разметку
const cleanText = (text) => text.replace(/\*\*(.+?)\*\*/g, '$1').replace(/^\s*[*-]\s+/gm, '• ')

function CarResult({ car, onOpen }) {
  return (
    <Link to={car.url} className="assistant-car" onClick={onOpen}>
      <span className="assistant-car-image">
        {car.image ? <img src={resolveMediaUrl(car.image)} alt="" loading="lazy" /> : <span>AutoBuy</span>}
      </span>
      <span className="assistant-car-info">
        <strong>{car.title}</strong>
        <span>{formatPrice(car.price, car.currency)}</span>
        <small>{[car.city, car.dealer].filter(Boolean).join(' · ')}</small>
        {car.murabaha && <em className="car-badge car-badge--murabaha">Мурабаха</em>}
      </span>
    </Link>
  )
}

function AdResult({ ad }) {
  // Баннер в чате — тоже показ: считаем его в статистике рекламодателя
  useEffect(() => { trackAdImpression(ad.id) }, [ad.id])
  const image = ad.mobile_image_url || ad.image_url
  return (
    <a href={adClickUrl(ad.id)} className="assistant-ad" target="_blank" rel="noopener sponsored">
      {image && <img src={resolveMediaUrl(image)} alt={ad.title} loading="lazy" />}
      <span><small>Реклама</small> {ad.advertiser}</span>
    </a>
  )
}

export default function AssistantChat() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState(loadHistory)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const listRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { saveHistory(messages) }, [messages])

  useEffect(() => {
    if (!open) return
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => { if (event.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  if (HIDDEN_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return null

  const send = async (text) => {
    const question = text.trim()
    if (!question || sending) return
    const next = [...messages, { role: 'user', text: question }]
    setMessages(next)
    setInput('')
    setError('')
    setSending(true)
    try {
      const data = await askAssistant(next.slice(-MAX_HISTORY).map(({ role, text: body }) => ({ role, text: body })))
      setMessages((current) => [...current, { role: 'model', text: data.reply, cars: data.cars || [], ads: data.ads || [] }])
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Помощник временно недоступен. Попробуйте позже.'))
    } finally {
      setSending(false)
    }
  }

  const reset = () => {
    setMessages([])
    setError('')
  }

  return (
    <>
      {open && (
        <section className="assistant-panel" role="dialog" aria-label="ИИ-помощник AutoBuy">
          <header className="assistant-header">
            <span className="assistant-avatar"><Sparkles size={18} /></span>
            <div>
              <strong>ИИ-помощник</strong>
              <small>Подбор авто и ответы о сайте</small>
            </div>
            {messages.length > 0 && <button type="button" className="assistant-reset" onClick={reset}>Новый чат</button>}
            <button type="button" className="assistant-close" onClick={() => setOpen(false)} aria-label="Закрыть"><X size={20} /></button>
          </header>

          <div className="assistant-messages" ref={listRef}>
            <div className="assistant-message assistant-message--model"><p>{GREETING}</p></div>
            {messages.length === 0 && (
              <div className="assistant-suggestions">
                {SUGGESTIONS.map((text) => (
                  <button key={text} type="button" onClick={() => send(text)}>{text}</button>
                ))}
              </div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`assistant-message assistant-message--${message.role}`}>
                <p>{message.role === 'model' ? cleanText(message.text) : message.text}</p>
                {message.ads?.length > 0 && (
                  <div className="assistant-cars">
                    {message.ads.map((ad) => <AdResult key={ad.id} ad={ad} />)}
                  </div>
                )}
                {message.cars?.length > 0 && (
                  <div className="assistant-cars">
                    {message.cars.map((car) => <CarResult key={car.id} car={car} onOpen={() => setOpen(false)} />)}
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="assistant-message assistant-message--model assistant-typing">
                <LoaderCircle className="spin" size={16} /> Думаю…
              </div>
            )}
            {error && <p className="assistant-error" role="alert">{error}</p>}
          </div>

          <form className="assistant-form" onSubmit={(event) => { event.preventDefault(); send(input) }}>
            <input
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              maxLength={1000}
              placeholder="Спросите что-нибудь…"
              aria-label="Сообщение помощнику"
            />
            <button type="submit" className="assistant-send" disabled={sending || !input.trim()} aria-label="Отправить">
              <SendHorizontal size={18} />
            </button>
          </form>
          <a className="assistant-whatsapp" href={whatsappLink(SUPPORT_PHONE, 'Здравствуйте! У меня вопрос по AutoBuy.')} target="_blank" rel="noopener noreferrer">
            <MessageCircle size={14} /> Нужен человек? Напишите нам в WhatsApp
          </a>
        </section>
      )}
      {!open && (
        <button type="button" className="assistant-fab" onClick={() => setOpen(true)} aria-label="Открыть ИИ-помощника">
          <Sparkles size={24} />
          <span>Спросить ИИ</span>
        </button>
      )}
    </>
  )
}
