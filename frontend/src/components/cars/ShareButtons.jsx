import { useState } from 'react'
import { Check, Link2, Send, Share2 } from 'lucide-react'
import { useToast } from '../../context/ToastContext.jsx'

export default function ShareButtons({ title, text }) {
  const { notify } = useToast()
  const [copied, setCopied] = useState(false)
  const url = typeof window === 'undefined' ? '' : window.location.href.split('#')[0]
  const message = `${text}\n${url}`
  const canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

  const nativeShare = async () => {
    try {
      await navigator.share({ title, text, url })
    } catch {
      // пользователь закрыл окно «Поделиться»
    }
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      const input = document.createElement('textarea')
      input.value = url
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      input.remove()
    }
    setCopied(true)
    notify('Ссылка скопирована.')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="share-block">
      <span className="share-label">Поделиться</span>
      <div className="share-buttons">
        <a className="share-button share-button--whatsapp" href={`https://wa.me/?text=${encodeURIComponent(message)}`} target="_blank" rel="noopener noreferrer" aria-label="Отправить в WhatsApp" title="WhatsApp">
          <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.4-.3Z" /></svg>
        </a>
        <a className="share-button share-button--telegram" href={`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`} target="_blank" rel="noopener noreferrer" aria-label="Отправить в Telegram" title="Telegram">
          <Send size={16} />
        </a>
        <button type="button" className="share-button" onClick={copyLink} aria-label="Скопировать ссылку" title="Скопировать ссылку">
          {copied ? <Check size={16} /> : <Link2 size={16} />}
        </button>
        {canNativeShare && (
          <button type="button" className="share-button" onClick={nativeShare} aria-label="Другие способы" title="Другие способы">
            <Share2 size={16} />
          </button>
        )}
      </div>
    </div>
  )
}
