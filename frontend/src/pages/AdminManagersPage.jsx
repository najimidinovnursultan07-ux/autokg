import { useCallback, useEffect, useState } from 'react'
import { Edit3, KeyRound, Plus, Power, Search, Trash2, Wand2 } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import {
  createAdminManager, deleteAdminManager, getAdminDealers, getAdminManagers,
  resetManagerPassword, updateAdminManager,
} from '../api/dealers.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const emptyForm = { email: '', first_name: '', last_name: '', phone: '', dealer: '', password: '' }

// Временный пароль: 14 символов, буквы разных регистров + цифры + символ
function generatePassword() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(12))
  const body = Array.from(bytes, (n) => alphabet[n % alphabet.length]).join('')
  return `${body}-${(bytes[0] % 90) + 10}`
}

export default function AdminManagersPage() {
  const { notify } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const dealerFilter = searchParams.get('dealer') || ''
  const [managers, setManagers] = useState([])
  const [dealers, setDealers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(null)
  const [issuedPassword, setIssuedPassword] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [list, dealerList] = await Promise.all([
        getAdminManagers(dealerFilter ? { dealer: dealerFilter } : {}),
        getAdminDealers(),
      ])
      setManagers(list)
      setDealers(dealerList)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить менеджеров.'))
    } finally {
      setLoading(false)
    }
  }, [dealerFilter])

  useEffect(() => { load() }, [load])

  const open = (manager) => {
    setEditing(manager || {})
    setForm(manager
      ? { email: manager.email, first_name: manager.first_name || '', last_name: manager.last_name || '', phone: manager.phone || '', dealer: String(manager.dealer || ''), password: '' }
      : { ...emptyForm, dealer: dealerFilter, password: generatePassword() })
  }

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form, dealer: Number(form.dealer), phone: form.phone || null }
      if (editing.id) {
        delete payload.password
        await updateAdminManager(editing.id, payload)
        notify('Менеджер обновлён.', 'success')
      } else {
        await createAdminManager(payload)
        setIssuedPassword({ email: payload.email, password: form.password })
      }
      setEditing(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сохранить менеджера.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (manager) => {
    try {
      await updateAdminManager(manager.id, { is_active: !manager.is_active })
      notify(manager.is_active ? 'Аккаунт отключён, активные сессии завершены.' : 'Аккаунт включён.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить статус.'), 'error')
    }
  }

  const submitReset = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await resetManagerPassword(resetting.id, resetting.password)
      setIssuedPassword({ email: resetting.email, password: resetting.password })
      setResetting(null)
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сменить пароль.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (manager) => {
    if (!window.confirm(`Удалить аккаунт ${manager.email}? Если у менеджера есть объявления, удаление будет отклонено — тогда отключите аккаунт.`)) return
    try {
      await deleteAdminManager(manager.id)
      notify('Менеджер удалён.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось удалить менеджера.'), 'error')
    }
  }

  const q = search.trim().toLowerCase()
  const visible = q
    ? managers.filter((m) => `${m.email} ${m.first_name} ${m.last_name} ${m.dealer_name}`.toLowerCase().includes(q))
    : managers
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Менеджеры салонов"
        description="Аккаунты для входа в кабинет салона. Публичной регистрации нет — менеджеров создаёте только вы."
        action={<button className="button button--primary" type="button" onClick={() => open(null)} disabled={!dealers.length}><Plus size={17} /> Добавить менеджера</button>}
      />

      <div className="admin-toolbar">
        <div className="admin-search-form">
          <Search size={18} />
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Email, имя или салон" aria-label="Поиск менеджеров" />
        </div>
        <select value={dealerFilter} onChange={(e) => setSearchParams(e.target.value ? { dealer: e.target.value } : {})} aria-label="Фильтр по салону">
          <option value="">Все салоны</option>
          {dealers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>

      {loading ? <LoadingState label="Загружаем менеджеров…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Менеджер</th><th>Салон</th><th>Последний вход</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>
              {visible.map((m) => (
                <tr key={m.id}>
                  <td><strong>{m.email}</strong><br /><small>{[m.first_name, m.last_name].filter(Boolean).join(' ') || '—'}</small></td>
                  <td>{m.dealer_name || '—'}{m.dealer_is_active === false && <><br /><small className="text-danger">салон отключён</small></>}</td>
                  <td>{m.last_login ? new Date(m.last_login).toLocaleString('ru-RU') : 'не входил'}</td>
                  <td><span className={`admin-status ${m.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{m.is_active ? 'Активен' : 'Отключён'}</span></td>
                  <td>
                    <div className="table-actions">
                      <button className="icon-action" type="button" onClick={() => open(m)} title="Изменить" aria-label="Изменить"><Edit3 size={16} /></button>
                      <button className="icon-action" type="button" onClick={() => setResetting({ id: m.id, email: m.email, password: generatePassword() })} title="Сбросить пароль" aria-label="Сбросить пароль"><KeyRound size={16} /></button>
                      <button className={`icon-action ${m.is_active ? 'icon-action--danger' : ''}`} type="button" onClick={() => toggleActive(m)} title={m.is_active ? 'Отключить' : 'Включить'} aria-label={m.is_active ? 'Отключить' : 'Включить'}><Power size={16} /></button>
                      <button className="icon-action icon-action--danger" type="button" onClick={() => remove(m)} title="Удалить" aria-label="Удалить"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visible.length && <div className="admin-empty">{dealers.length ? 'Менеджеров пока нет.' : 'Сначала создайте автосалон.'}</div>}
        </div>
      )}

      {editing && (
        <div className="admin-modal-backdrop" role="presentation">
          <form className="admin-modal admin-modal--wide" role="dialog" aria-modal="true" aria-labelledby="manager-form-title" onSubmit={save}>
            <h2 id="manager-form-title">{editing.id ? 'Редактировать менеджера' : 'Новый менеджер'}</h2>
            <div className="form-grid">
              <label className="field-label">Email *<input type="email" required value={form.email} onChange={set('email')} /></label>
              <label className="field-label">Салон *<select required value={form.dealer} onChange={set('dealer')}><option value="">Выберите салон</option>{dealers.map((d) => <option key={d.id} value={d.id}>{d.name}{d.is_active ? '' : ' (отключён)'}</option>)}</select></label>
              <label className="field-label">Имя<input value={form.first_name} onChange={set('first_name')} /></label>
              <label className="field-label">Фамилия<input value={form.last_name} onChange={set('last_name')} /></label>
              <label className="field-label">Телефон<input type="tel" value={form.phone} onChange={set('phone')} placeholder="+996700123456" /></label>
              {!editing.id && (
                <label className="field-label">Временный пароль *
                  <span className="field-range">
                    <input required minLength={12} value={form.password} onChange={set('password')} />
                    <button type="button" className="button button--outline" onClick={() => setForm({ ...form, password: generatePassword() })} title="Сгенерировать"><Wand2 size={15} /></button>
                  </span>
                </label>
              )}
            </div>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setEditing(null)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
            </div>
          </form>
        </div>
      )}

      {resetting && (
        <div className="admin-modal-backdrop" role="presentation">
          <form className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="reset-title" onSubmit={submitReset}>
            <h2 id="reset-title">Новый пароль для {resetting.email}</h2>
            <p>Все активные сессии менеджера будут завершены.</p>
            <label className="field-label">Пароль
              <span className="field-range">
                <input required minLength={12} value={resetting.password} onChange={(e) => setResetting({ ...resetting, password: e.target.value })} />
                <button type="button" className="button button--outline" onClick={() => setResetting({ ...resetting, password: generatePassword() })} title="Сгенерировать"><Wand2 size={15} /></button>
              </span>
            </label>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setResetting(null)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Сохраняем…' : 'Сменить пароль'}</button>
            </div>
          </form>
        </div>
      )}

      {issuedPassword && (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="issued-title">
            <h2 id="issued-title">Данные для входа</h2>
            <p>Передайте менеджеру безопасным способом. Пароль больше не будет показан.</p>
            <div className="credentials-box">
              <span>Email: <strong>{issuedPassword.email}</strong></span>
              <span>Пароль: <strong>{issuedPassword.password}</strong></span>
              <span>Вход: <strong>{window.location.origin}/login</strong></span>
            </div>
            <div className="admin-modal-actions">
              <button type="button" className="button button--outline" onClick={() => navigator.clipboard?.writeText(`${issuedPassword.email}\n${issuedPassword.password}`).then(() => notify('Скопировано.', 'success'))}>Скопировать</button>
              <button type="button" className="button button--primary" onClick={() => setIssuedPassword(null)}>Готово</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
