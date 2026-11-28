import { CarFront, CircleHelp, Mail, MapPin, MessageCircle, Phone, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { SUPPORT_PHONE, SUPPORT_PHONE_DIGITS } from '../utils/contacts.js'
import { usePageMeta } from '../hooks/usePageMeta.js'

function ContactActions({ message }) {
  return (
    <div className="contact-actions">
      <a className="contact-phone" href={`tel:+${SUPPORT_PHONE_DIGITS}`}><Phone size={15} /> {SUPPORT_PHONE}</a>
      <a
        className="seller-whatsapp contact-whatsapp"
        href={`https://wa.me/${SUPPORT_PHONE_DIGITS}?text=${encodeURIComponent(message)}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        <MessageCircle size={16} /> Написать в WhatsApp
      </a>
    </div>
  )
}

export default function ContactsPage() {
  usePageMeta('Контакты')
  const supportEmail = import.meta.env.VITE_SUPPORT_EMAIL
  return (
    <section className="container page-section">
      <div className="contact-hero">
        <span className="eyebrow">Мы на связи</span>
        <h1>Есть вопрос?<br /><em>Давайте обсудим.</em></h1>
        <p>Поможем разобраться с размещением объявления или работой платформы.</p>
      </div>
      <div className="contact-grid">
        <Link className="contact-card" to="/catalog"><span className="contact-icon"><Search size={20} /></span><span className="eyebrow">Покупателям</span><strong>Найти автомобиль</strong><small>Свяжитесь с салоном по телефону или WhatsApp.</small></Link>
        <div className="contact-card"><span className="contact-icon"><CarFront size={20} /></span><span className="eyebrow">Автосалонам</span><strong>Подключить автосалон</strong><small>Размещать объявления могут только автосалоны-партнёры. Напишите нам, чтобы подключить салон.</small><ContactActions message="Здравствуйте! Хочу подключить автосалон к AutoBuy." /></div>
        {supportEmail ? (
          <a className="contact-card" href={`mailto:${supportEmail}`}><span className="contact-icon"><Mail size={20} /></span><span className="eyebrow">Поддержка</span><strong>{supportEmail}</strong><small>Напишите нам по вопросам работы площадки.</small></a>
        ) : (
          <div className="contact-card"><span className="contact-icon"><CircleHelp size={20} /></span><span className="eyebrow">Поддержка</span><strong>AutoBuy для всей страны</strong><small>Если вопрос связан с объявлением, свяжитесь с автосалоном по телефону или WhatsApp. По работе площадки — пишите нам.</small><ContactActions message="Здравствуйте! У меня вопрос по AutoBuy." /></div>
        )}
      </div>
      <div className="contact-bottom"><p><MapPin size={17} /> Платформа для покупателей и продавцов по всему Кыргызстану</p><Link className="button button--primary" to="/about">О проекте</Link></div>
    </section>
  )
}
