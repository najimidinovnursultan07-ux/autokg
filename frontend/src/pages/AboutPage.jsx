import { ArrowRight, BadgeCheck, CarFront, HeartHandshake, SearchCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { usePageMeta } from '../hooks/usePageMeta.js'

const values = [
  { icon: SearchCheck, title: 'Понятный поиск', text: 'Фильтры и характеристики помогают сравнивать объявления без лишних шагов.' },
  { icon: BadgeCheck, title: 'Качество объявлений', text: 'Объявления проходят модерацию перед появлением в публичном каталоге.' },
  { icon: HeartHandshake, title: 'Прямой контакт', text: 'Покупатель связывается с продавцом напрямую и договаривается об осмотре.' },
]

export default function AboutPage() {
  usePageMeta('О сервисе')
  return (
    <section className="container page-section">
      <div className="about-hero">
        <span className="eyebrow">О платформе</span>
        <h1>Автомобильный рынок<br /><em>ближе и понятнее</em></h1>
        <p>AutoBuy — площадка для покупки и продажи автомобилей в Кыргызстане. Мы помогаем находить объявления, сравнивать автомобили и удобно управлять продажей.</p>
        <Link className="button button--primary" to="/catalog">Открыть каталог <ArrowRight size={17} /></Link>
      </div>
      <div className="about-values">{values.map(({ icon: Icon, title, text }) => <article className="about-value" key={title}><span className="value-icon"><Icon size={20} /></span><h2>{title}</h2><p>{text}</p></article>)}</div>
      <div className="about-note"><CarFront size={27} /><div><h2>Покупайте и продавайте с уверенностью</h2><p>Проверяйте автомобиль лично, уточняйте историю и не переводите предоплату незнакомым людям.</p></div></div>
    </section>
  )
}
