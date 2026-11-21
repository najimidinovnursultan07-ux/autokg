import { ArrowUpRight, Mail, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

const currentYear = new Date().getFullYear()

export default function Footer() {
  const supportEmail = import.meta.env.VITE_SUPPORT_EMAIL
  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div className="footer-brand-column">
          <Link className="brand brand--footer" to="/">
            <span className="brand-name">Auto<span>Buy</span></span>
          </Link>
          <p>Платформа, которая соединяет людей и автомобили по всему Кыргызстану.</p>
        </div>
        <div className="footer-column">
          <h3>Покупателям</h3>
          <Link to="/catalog">Каталог автомобилей</Link>
          <Link to="/dealers">Автосалоны</Link>
          <Link to="/about">Как это работает</Link>
        </div>
        <div className="footer-column">
          <h3>AutoBuy</h3>
          <Link to="/about">О проекте</Link>
          <Link to="/pricing">Тарифы для автосалонов</Link>
          <Link to="/contacts">Контакты</Link>
        </div>
        <div className="footer-column footer-contact">
          <h3>Связаться с нами</h3>
          <span><MapPin size={15} /> Работаем по всему Кыргызстану</span>
          {supportEmail ? (
            <a href={`mailto:${supportEmail}`}><Mail size={15} /> {supportEmail} <ArrowUpRight size={14} /></a>
          ) : (
            <Link to="/contacts">Помощь и контакты <ArrowUpRight size={14} /></Link>
          )}
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {currentYear} AutoBuy. Все права защищены.</span>
        <span>Сделано с заботой об автолюбителях Кыргызстана</span>
      </div>
    </footer>
  )
}
