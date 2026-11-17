import { useCallback, useEffect, useState } from 'react'
import { Ban, Search, ShieldCheck, UserRoundCheck } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { blockAdminUser, getAdminUsers, unblockAdminUser } from '../api/admin.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const PAGE_SIZE = 10
const dateFormatter = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium' })

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const { notify } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') || ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const activeFilter = searchParams.get('is_active') || ''
  const [searchInput, setSearchInput] = useState(search)
  const [users, setUsers] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getAdminUsers({
        search: search || undefined,
        is_active: activeFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      setUsers(response.results || [])
      setCount(response.count || 0)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить пользователей.'))
    } finally {
      setLoading(false)
    }
  }, [activeFilter, page, search])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setSearchInput(search)
  }, [search])

  const applySearch = (event) => {
    event.preventDefault()
    const next = new URLSearchParams(searchParams)
    const value = searchInput.trim()
    if (value) next.set('search', value)
    else next.delete('search')
    next.delete('page')
    setSearchParams(next)
  }

  const setActiveFilter = (value) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('is_active', value)
    else next.delete('is_active')
    next.delete('page')
    setSearchParams(next)
  }

  const changePage = (nextPage) => {
    const next = new URLSearchParams(searchParams)
    if (nextPage > 1) next.set('page', String(nextPage))
    else next.delete('page')
    setSearchParams(next)
  }

  const toggleBlock = async (target) => {
    const shouldBlock = target.is_active
    const title = target.email
    if (shouldBlock && !window.confirm(`Заблокировать пользователя ${title}? Его активные сессии будут отозваны.`)) return
    setWorkingId(target.id)
    try {
      if (shouldBlock) await blockAdminUser(target.id)
      else await unblockAdminUser(target.id)
      notify(shouldBlock ? 'Пользователь заблокирован.' : 'Пользователь разблокирован.', 'success')
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось изменить статус пользователя.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Пользователи" description="Поиск аккаунтов, просмотр профилей и управление доступом." />
      <div className="admin-toolbar">
        <form className="admin-search-form" onSubmit={applySearch}>
          <Search size={18} />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Email, имя, фамилия или телефон"
            aria-label="Поиск пользователей"
          />
          <button type="submit" className="button button--primary">Найти</button>
        </form>
        <select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)} aria-label="Фильтр по статусу">
          <option value="">Все аккаунты</option>
          <option value="true">Активные</option>
          <option value="false">Заблокированные</option>
        </select>
      </div>

      {loading ? <LoadingState label="Загружаем пользователей…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : users.length ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Пользователь</th><th>Телефон</th><th>Статус</th><th>Объявления</th><th>Регистрация</th><th>Действие</th></tr></thead>
              <tbody>
                {users.map((item) => {
                  const isAdmin = item.role === 'admin'
                  const isSelf = item.id === currentUser?.id
                  return (
                    <tr key={item.id}>
                      <td>
                        <div className="admin-user-cell">
                          <span className={`admin-user-avatar ${isAdmin ? 'admin-user-avatar--staff' : ''}`}>
                            {isAdmin ? <ShieldCheck size={17} /> : <span>{item.first_name?.[0] || item.email[0]}</span>}
                          </span>
                          <span><strong>{[item.first_name, item.last_name].filter(Boolean).join(' ') || 'Без имени'}</strong><small>{item.email}</small></span>
                        </div>
                      </td>
                      <td>{item.phone || '—'}</td>
                      <td><span className={`admin-status ${item.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{item.is_active ? 'Активен' : 'Заблокирован'}</span></td>
                      <td>{item.listings_count}</td>
                      <td>{item.date_joined ? dateFormatter.format(new Date(item.date_joined)) : '—'}</td>
                      <td>
                        {isAdmin ? <span className="admin-protected-label">Администратор</span> : (
                          <button
                            type="button"
                            className={`admin-action-button ${item.is_active ? 'admin-action-button--danger' : 'admin-action-button--success'}`}
                            disabled={workingId === item.id || isSelf}
                            onClick={() => toggleBlock(item)}
                          >
                            {item.is_active ? <><Ban size={15} /> Заблокировать</> : <><UserRoundCheck size={15} /> Разблокировать</>}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <AdminPagination page={page} pageCount={pageCount} count={count} changePage={changePage} />
        </>
      ) : <div className="admin-empty">Пользователи не найдены.</div>}
    </section>
  )
}

function AdminPagination({ page, pageCount, count, changePage }) {
  if (!pageCount) return null
  return (
    <div className="admin-pagination">
      <span>{count} пользователей · страница {page} из {pageCount}</span>
      <div>
        <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => changePage(page - 1)}>Назад</button>
        <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => changePage(page + 1)}>Далее</button>
      </div>
    </div>
  )
}
