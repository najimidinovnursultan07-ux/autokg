import { Star } from 'lucide-react'

export function pluralReviews(n) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'отзыв'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'отзыва'
  return 'отзывов'
}

/** Звёзды для показа оценки (дробная часть закрашивается частично). */
export function Stars({ value = 0, size = 16 }) {
  return (
    <span className="stars" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((n) => {
        const fill = Math.max(0, Math.min(1, value - (n - 1)))
        return (
          <span key={n} className="star" style={{ width: size, height: size }}>
            <Star size={size} className="star-empty" />
            <span className="star-fill" style={{ width: `${fill * 100}%` }}><Star size={size} /></span>
          </span>
        )
      })}
    </span>
  )
}

/** «★★★★☆ 4.5 · 12 отзывов» или «Нет отзывов». */
export default function StarRating({ rating, count = 0, size = 16, compact = false }) {
  if (!count) return compact ? null : <span className="star-rating star-rating--empty">Пока нет отзывов</span>
  return (
    <span className="star-rating" aria-label={`Рейтинг ${rating} из 5, ${count} ${pluralReviews(count)}`}>
      <Stars value={rating} size={size} />
      <strong>{Number(rating).toFixed(1)}</strong>
      <span>· {count} {pluralReviews(count)}</span>
    </span>
  )
}

/** Выбор оценки в форме отзыва. */
export function StarInput({ value, onChange }) {
  return (
    <div className="star-input" role="radiogroup" aria-label="Оценка">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} из 5`}
          className={n <= value ? 'is-active' : ''}
          onClick={() => onChange(n)}
        >
          <Star size={28} />
        </button>
      ))}
    </div>
  )
}
