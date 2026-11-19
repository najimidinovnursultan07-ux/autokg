import { useCallback, useEffect, useState } from 'react'
import { Building2, Plus, Power, Trash2, Edit3 } from 'lucide-react'
import {
  createAdminDealer, deleteAdminDealer, getAdminDealers,
  toggleDealerActive, updateAdminDealer,
} from '../api/dealers.js'
import { LoadingState, ErrorState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function AdminDealersPage() {
  const { notify } = useToast()
  const [dealers, setDealers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editDealer, setEditDealer] = useState(null)
  const [form, setForm] = useState({ name: '', phone: '', whatsapp: '', address: '', description: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setDealers(await getAdminDealers()) }
    catch (err) { setError(getErrorMessage(err, 'Ошибка загрузки.')) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditDealer(null); setForm({ name: '', phone: '', whatsapp: '', address: '', description: '' }); setShowForm(true) }
  const openEdit = (d) => { setEditDealer(d); setForm({ name: d.name, phone: d.phone || '', whatsapp: d.whatsapp || '', address: d.address || '', description: d.description || '' }); setShowForm(true) }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editDealer) {
        await updateAdminDealer(editDealer.id, form)
        notify('Салон обновлён.', 'success')
      } else {
        await createAdminDealer(form)
        notify('Салон создан.', 'success')
      }
      setShowForm(false)
      await load()
    } catch (err) { notify(getErrorMessage(err, 'Ошибка.'), 'error') }
    finally { setSaving(false) }
  }

  const toggle = async (dealer) => {
    try {
      await toggleDealerActive(dealer.id)
      notify(dealer.is_active ? 'Салон отключён.' : 'Салон включён.', 'success')
      await load()
    } catch (err) { notify(getErrorMessage(err, 'Ошибка.'), 'error') }
  }

  const remove = async (dealer) => {
    if (!window.confirm(`Удалить «${dealer.name}»?`)) return
    try {
      await deleteAdminDealer(dealer.id)
      notify('Салон удалён.', 'success')
      await load()
    } catch (err) { notify(getErrorMessage(err, 'Ошибка.'), 'error') }
  }

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Автосалоны"
        description="Управляйте партнёрами платформы."
        action={<button className="button button--primary" onClick={openCreate}><Plus size={17} /> Добавить салон</button>}
      />

      {showForm && (
        <div className="modal-backdrop">
          <form className="modal-box" onSubmit={save}>
            <h2>{editDealer ? 'Редактировать салон' : 'Новый салон'}</h2>
            <div className="form-stack">
              <label className="field-label">Название *<input required value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></label>
              <label className="field-label">Телефон<input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></label>
              <label className="field-label">WhatsApp<input value={form.whatsapp} onChange={e => setForm({...form, whatsapp: e.target.value})} /></label>
              <label className="field-label">Адрес<input value={form.address} onChange={e => setForm({...form, address: e.target.value})} /></label>
              <label className="field-label">Описание<textarea rows={3} value={form.description} onChange={e => setForm({...form, description: e.target.value})} /></label>
            </div>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setShowForm(false)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
            </div>
          </form>
        </div>
      )}

      {loading ? <LoadingState label="Загружаем салоны…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Салон</th><th>Телефон</th><th>Авто</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>
              {dealers.map(d => (
                <tr key={d.id}>
                  <td><strong>{d.name}</strong><br /><small>{d.slug}</small></td>
                  <td>{d.phone || '—'}</td>
                  <td>{d.car_count || 0}</td>
                  <td><span className={`admin-status ${d.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{d.is_active ? 'Активен' : 'Отключён'}</span></td>
                  <td>
                    <div style={{display:'flex', gap:'6px'}}>
                      <button className="icon-action" onClick={() => openEdit(d)} title="Редактировать"><Edit3 size={16} /></button>
                      <button className={`icon-action ${d.is_active ? 'icon-action--danger' : ''}`} onClick={() => toggle(d)} title={d.is_active ? 'Отключить' : 'Включить'}><Power size={16} /></button>
                      <button className="icon-action icon-action--danger" onClick={() => remove(d)} title="Удалить"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!dealers.length && <div className="admin-empty">Салоны не добавлены.</div>}
        </div>
      )}
    </section>
  )
}
