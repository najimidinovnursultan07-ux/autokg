import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Горизонтальная лента в стиле мобильного приложения:
 * заголовок + кнопка «Все», прокрутка свайпом, стрелки на десктопе.
 */
export default function Shelf({ title, icon, allTo, allLabel = 'Все', children, variant = '' }) {
  const trackRef = useRef(null)

  const scroll = (direction) => {
    const track = trackRef.current
    if (!track) return
    track.scrollBy({ left: direction * track.clientWidth * 0.85, behavior: 'smooth' })
  }

  return (
    <section className={`shelf ${variant ? `shelf--${variant}` : ''}`}>
      <div className="shelf-head container">
        <h2>{icon}{title}</h2>
        <div className="shelf-head-actions">
          <button type="button" className="shelf-arrow" onClick={() => scroll(-1)} aria-label="Прокрутить назад"><ChevronLeft size={18} /></button>
          <button type="button" className="shelf-arrow" onClick={() => scroll(1)} aria-label="Прокрутить вперёд"><ChevronRight size={18} /></button>
          {allTo && <Link className="shelf-all" to={allTo}>{allLabel} <ChevronRight size={16} /></Link>}
        </div>
      </div>
      <div className="shelf-track" ref={trackRef}>
        {children}
      </div>
    </section>
  )
}

// Заглушки внутри ленты, пока идёт загрузка
export function ShelfSkeleton({ count = 4, variant = 'card' }) {
  return Array.from({ length: count }, (_, i) => (
    <div key={i} className={`skeleton skeleton--${variant}`} aria-hidden="true" />
  ))
}
