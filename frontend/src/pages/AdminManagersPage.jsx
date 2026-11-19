import { useCallback, useEffect, useState } from 'react'
import { Plus, UserX } from 'lucide-react'
import { createAdminManager, getAdminDealers, getAdminManagers, updateAdminManager } from '../api/dealers.js'
import { LoadingState, ErrorState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function AdminManagersPage() {
  const { notify } = useToast()
  const [managers, setManagers] = useState([])
  const [dealers, setDealers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', dealer_id: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [m, d] = await Promise.all([getAdminManagers(), getAdminDealers()])
      setManagers(m); setDealers(d)
    } catch (err) { }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await createAdminManager(form)
      notify('Менеджер создан.', 'success')
      setShowForm(false)
      await load()
    } catch (err) { notify(getErrorMessage(err, 'Ошибка.'), 'error') }
    finally { setSaving(false) }
  }

  const toggle = async (manager) => {
    try {
      await updateAdminManager(manager.id, { is_active: !manager.is_active })
      notify(manager.is_active ? 'Отключён.' : 'Включён.', 'success')
      await load()
    } catch (err) { notify(getErrorMessage(err, 'Ошибка.'), 'error') }
  }

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Менеджеры"
        description="Аккаунты дилеров автосалонов."
        action={<button className="button button--primary" onClick={() => setShowForm(true)}><Plus size={17} /> Добавить менеджера</button>}
      />

      {showForm && (
        <div className="modal-backdrop">
          <form className="modal-box" onSubmit={save}>
            <h2>Новый менеджер</h2>
            <div className="form-stack">
              <label className="field-label">Email *<input required type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></label>
              <label className="field-label">Пароль *<input required type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} /></label>
              <label className="field-label">Имя<input value={form.first_name} onChange={e => setForm({...form, first_name: e.target.value})} /></label>
              <label className="field-label">Фамилия<input value={form.last_name} onChange={e => setForm({...form, last_name: e.target.value})} /></label>
              <label className="field-label">Автосалон
                <select value={form.dealer_id} onChange={e => setForm({...form, dealer_id: e.target.value})}>
                  <option value="">— Без салона —</option>
                  {dealers.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </label>
            </div>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setShowForm(false)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Создаём…' : 'Создать'}</button>
            </div>
          </form>
        </div>
      )}

      {loading ? <LoadingState label="Загружаем…" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Email</th><th>Имя</th><th>Салон</th><th>Статус</th><th></th></tr></thead>
            <tbody>
              {managers.map(m => (
                <tr key={m.id}>
                  <td>{m.email}</td>
                  <td>{[m.first_name, m.last_name].filter(Boolean).join(' ') || '—'}</td>
                  <td>{m.dealer_name || '—'}</td>
                  <td><span className={`admin-status ${m.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{m.is_active ? 'Активен' : 'Отключён'}</span></td>
                  <td>
                    <button className={`admin-action-button ${m.is_active ? 'admin-action-button--danger' : 'admin-action-button--success'}`}
                      onClick={() => toggle(m)}>
                      <UserX size={15} /> {m.is_active ? 'Отключить' : 'Включить'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!managers.length && <div className="admin-empty">Менеджеры не добавлены.</div>}
        </div>
      )}
    </section>
  )
}
