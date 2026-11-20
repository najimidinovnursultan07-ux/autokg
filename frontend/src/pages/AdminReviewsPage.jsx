import { useCallback, useEffect, useState } from 'react'
import { Check, ChevronLeft, ChevronRight, EyeOff, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { deleteAdminReview, getAdminReviews, updateAdminReview } from '../api/dealers.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { Stars } from '../components/dealers/StarRating.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatDate } from '../utils/format.js'

const PAGE_SIZE = 20
const STATUS_TABS = [
  ['pending', 'На проверке'],
  ['published', 'Опубликованные'],
  ['rejected', 'Отклонённые'],
  ['', 'Все'],
]
const STATUS_LABELS = { pending: 'На проверке', published: 'Опубликован', rejected: 'Отклонён' }

export default function AdminReviewsPage() {
  const { notify } = useToast()
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const [reviews, setReviews] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getAdminReviews({ status: status || undefined, page })
      setReviews(data.results)
      setCount(data.count)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить отзывы.'))
    } finally {
      setLoading(false)
    }
  }, [status, page])

  useEffect(() => { load() }, [load])

  const changeStatus = async (review, nextStatus, message) => {
    setWorkingId(review.id)
    try {
      await updateAdminReview(review.id, { status: nextStatus })
      notify(message, 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить отзыв.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const remove = async (review) => {
    if (!window.confirm(`Удалить отзыв «${review.author_name}» навсегда?`)) return
    setWorkingId(review.id)
    try {
      await deleteAdminReview(review.id)
      notify('Отзыв удалён.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось удалить отзыв.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Отзывы о салонах" description="Новые отзывы появляются на сайте только после публикации." />
      <div className="admin-tabs" role="tablist">
        {STATUS_TABS.map(([value, label]) => (
          <button
            key={value || 'all'}
            type="button"
            role="tab"
            aria-selected={status === value}
            className={`admin-tab ${status === value ? 'admin-tab--active' : ''}`}
            onClick={() => { setStatus(value); setPage(1) }}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? <LoadingState label="Загружаем отзывы…" /> : error ? <ErrorState message={error} onRetry={load} /> : reviews.length ? (
        <>
          <ul className="admin-review-list">
            {reviews.map((review) => {
              const busy = workingId === review.id
              return (
                <li key={review.id} className="admin-review">
                  <div className="admin-review-top">
                    <Stars value={review.rating} size={15} />
                    <strong>{review.author_name}</strong>
                    <span>о салоне <Link to={`/dealers/${review.dealer_slug}`} target="_blank">{review.dealer_name}</Link></span>
                    <span className={`admin-status admin-status--${review.status}`}>{STATUS_LABELS[review.status]}</span>
                    <small>{formatDate(review.created_at)}</small>
                  </div>
                  <p>{review.text}</p>
                  <div className="table-actions">
                    {review.status !== 'published' && (
                      <button type="button" className="button button--primary" disabled={busy}
                        onClick={() => changeStatus(review, 'published', 'Отзыв опубликован.')}><Check size={16} /> Опубликовать</button>
                    )}
                    {review.status !== 'rejected' && (
                      <button type="button" className="button button--outline" disabled={busy}
                        onClick={() => changeStatus(review, 'rejected', 'Отзыв отклонён и скрыт с сайта.')}><EyeOff size={16} /> Отклонить</button>
                    )}
                    <button type="button" className="icon-action icon-action--danger" disabled={busy} onClick={() => remove(review)} title="Удалить" aria-label="Удалить"><Trash2 size={16} /></button>
                  </div>
                </li>
              )
            })}
          </ul>
          {pageCount > 1 && (
            <div className="pagination">
              <button type="button" className="icon-action" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Назад"><ChevronLeft size={16} /></button>
              <span>{page} / {pageCount}</span>
              <button type="button" className="icon-action" disabled={page >= pageCount} onClick={() => setPage(page + 1)} aria-label="Вперёд"><ChevronRight size={16} /></button>
            </div>
          )}
        </>
      ) : (
        <p className="empty-inline">{status === 'pending' ? 'Новых отзывов на проверку нет.' : 'Отзывов нет.'}</p>
      )}
    </section>
  )
}
