import { useCallback, useEffect, useState } from 'react'
import { MessageSquarePlus } from 'lucide-react'
import { createDealerReview, getDealerReviews } from '../../api/dealers.js'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'
import { formatDate } from '../../utils/format.js'
import StarRating, { StarInput, Stars } from './StarRating.jsx'

const EMPTY = { author_name: '', rating: 0, text: '', website: '' }

export default function DealerReviews({ dealer }) {
  const { notify } = useToast()
  const [reviews, setReviews] = useState([])
  const [next, setNext] = useState(null)
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [sending, setSending] = useState(false)
  const [errors, setErrors] = useState({})
  const [sent, setSent] = useState(false)

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const data = await getDealerReviews(dealer.slug, page)
      setReviews((prev) => (page === 1 ? data.results : [...prev, ...data.results]))
      setNext(data.next ? page + 1 : null)
    } catch {
      // отзывы — не критичная часть страницы салона
    } finally {
      setLoading(false)
    }
  }, [dealer.slug])

  useEffect(() => { load(1) }, [load])

  const submit = async (event) => {
    event.preventDefault()
    if (!form.rating) {
      setErrors({ rating: 'Поставьте оценку от 1 до 5 звёзд.' })
      return
    }
    setSending(true)
    setErrors({})
    try {
      await createDealerReview(dealer.slug, form)
      setForm(EMPTY)
      setSent(true)
      setFormOpen(false)
      notify('Спасибо! Отзыв появится после проверки.', 'success')
    } catch (requestError) {
      const data = requestError.response?.data
      if (data && typeof data === 'object' && !data.detail) {
        setErrors(Object.fromEntries(Object.entries(data).map(([key, value]) => [key, [].concat(value).join(' ')])))
      } else {
        notify(getErrorMessage(requestError, 'Не удалось отправить отзыв.'), 'error')
      }
    } finally {
      setSending(false)
    }
  }

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  return (
    <section className="dealer-reviews">
      <div className="dealer-reviews-head">
        <div>
          <h2>Отзывы о салоне</h2>
          <StarRating rating={dealer.rating} count={dealer.reviews_count} size={18} />
        </div>
        {!formOpen && (
          <button type="button" className="button button--outline" onClick={() => { setFormOpen(true); setSent(false) }}>
            <MessageSquarePlus size={17} /> Оставить отзыв
          </button>
        )}
      </div>

      {sent && <p className="dealer-review-notice">Спасибо! Ваш отзыв отправлен и появится на сайте после проверки.</p>}

      {formOpen && (
        <form className="dealer-review-form" onSubmit={submit} noValidate>
          <label className="field-label">Ваша оценка
            <StarInput value={form.rating} onChange={(rating) => setForm({ ...form, rating })} />
            {errors.rating && <small className="field-error">{errors.rating}</small>}
          </label>
          <label className="field-label">Имя
            <input required maxLength="80" value={form.author_name} onChange={set('author_name')} placeholder="Как к вам обращаться" />
            {errors.author_name && <small className="field-error">{errors.author_name}</small>}
          </label>
          <label className="field-label">Отзыв
            <textarea required rows="4" maxLength="2000" value={form.text} onChange={set('text')} placeholder="Расскажите, как прошла покупка: обслуживание, честность, сроки…" />
            {errors.text && <small className="field-error">{errors.text}</small>}
          </label>
          {/* Ловушка для ботов: скрыта от людей */}
          <input className="hp-field" tabIndex="-1" autoComplete="off" value={form.website} onChange={set('website')} aria-hidden="true" />
          <div className="dealer-review-actions">
            <button type="button" className="button button--outline" onClick={() => setFormOpen(false)}>Отмена</button>
            <button type="submit" className="button button--primary" disabled={sending}>{sending ? 'Отправляем…' : 'Отправить отзыв'}</button>
          </div>
          <small className="dealer-review-hint">Отзывы проверяет модератор: публикуем честные отзывы без оскорблений и рекламы.</small>
        </form>
      )}

      {reviews.length > 0 ? (
        <ul className="dealer-review-list">
          {reviews.map((review) => (
            <li key={review.id} className="dealer-review">
              <div className="dealer-review-top">
                <strong>{review.author_name}</strong>
                <Stars value={review.rating} size={14} />
                <span>{formatDate(review.created_at)}</span>
              </div>
              <p>{review.text}</p>
            </li>
          ))}
        </ul>
      ) : !loading && !formOpen && (
        <p className="dealer-review-empty">Пока никто не оставил отзыв. Покупали здесь машину? Расскажите другим.</p>
      )}

      {next && (
        <button type="button" className="button button--outline dealer-review-more" onClick={() => load(next)} disabled={loading}>
          {loading ? 'Загружаем…' : 'Показать ещё'}
        </button>
      )}
    </section>
  )
}
