import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <section className="container not-found">
      <span className="not-found-code">404</span>
      <span className="eyebrow">Страница не найдена</span>
      <h1>Кажется, мы свернули не туда</h1>
      <p>Эта страница не существует или была перемещена.</p>
      <Link to="/" className="button button--primary"><ArrowLeft size={17} /> На главную</Link>
    </section>
  )
}
