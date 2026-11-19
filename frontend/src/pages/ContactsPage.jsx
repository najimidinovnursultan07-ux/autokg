import { CarFront, CircleHelp, Mail, MapPin, Search } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function ContactsPage() {
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
        <Link className="contact-card" to="/login"><span className="contact-icon"><CarFront size={20} /></span><span className="eyebrow">Автосалонам</span><strong>Вход для автосалонов</strong><small>Доступ в кабинет выдаёт администратор AutoKG — напишите нам, чтобы подключить салон.</small></Link>
        {supportEmail ? (
          <a className="contact-card" href={`mailto:${supportEmail}`}><span className="contact-icon"><Mail size={20} /></span><span className="eyebrow">Поддержка</span><strong>{supportEmail}</strong><small>Напишите нам по вопросам работы площадки.</small></a>
        ) : (
          <div className="contact-card"><span className="contact-icon"><CircleHelp size={20} /></span><span className="eyebrow">Поддержка</span><strong>AutoKG для всей страны</strong><small>Если вопрос связан с объявлением, используйте контакты продавца или управление в личном кабинете.</small></div>
        )}
      </div>
      <div className="contact-bottom"><p><MapPin size={17} /> Платформа для покупателей и продавцов по всему Кыргызстану</p><Link className="button button--primary" to="/about">О проекте</Link></div>
    </section>
  )
}
