import { useCallback, useEffect, useMemo, useState } from 'react'
import { Building2, Edit3, ImagePlus, Plus, Power, Search, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getLookups } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import {
  createAdminDealer, deleteAdminDealer, getAdminDealers,
  toggleDealerActive, updateAdminDealer,
} from '../api/dealers.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const emptyForm = { name: '', slug: '', phone: '', whatsapp: '', address: '', city: '', description: '', is_active: true }
const MAX_LOGO = 5 * 1024 * 1024

export default function AdminDealersPage() {
  const { notify } = useToast()
  const [dealers, setDealers] = useState([])
  const [cities, setCities] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null) // null — закрыто, {} — новый, dealer — правка
  const [form, setForm] = useState(emptyForm)
  const [logoFile, setLogoFile] = useState(null)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const logoPreview = useMemo(() => (logoFile ? URL.createObjectURL(logoFile) : ''), [logoFile])
  useEffect(() => () => logoPreview && URL.revokeObjectURL(logoPreview), [logoPreview])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [list, lookups] = await Promise.all([getAdminDealers(), getLookups()])
      setDealers(list)
      setCities(lookups.cities)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить салоны.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const open = (dealer) => {
    setEditing(dealer || {})
    setLogoFile(null)
    setForm(dealer
      ? Object.fromEntries(Object.keys(emptyForm).map((k) => [k, dealer[k] ?? emptyForm[k]]))
      : emptyForm)
  }

  const pickLogo = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return notify('Логотип: только JPG, PNG или WEBP.', 'error')
    if (file.size > MAX_LOGO) return notify('Логотип: не более 5 МБ.', 'error')
    setLogoFile(file)
  }

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = new FormData()
      Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ''))
      if (logoFile) payload.append('logo', logoFile)
      if (editing.id) {
        await updateAdminDealer(editing.id, payload)
        notify('Салон обновлён.', 'success')
      } else {
        await createAdminDealer(payload)
        notify('Салон создан. Теперь добавьте ему менеджера.', 'success')
      }
      setEditing(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сохранить салон.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggle = async (dealer) => {
    try {
      await toggleDealerActive(dealer.id)
      notify(dealer.is_active ? 'Салон отключён: его объявления скрыты, менеджеры не могут публиковать.' : 'Салон включён.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить статус.'), 'error')
    }
  }

  const remove = async () => {
    try {
      await deleteAdminDealer(confirmDelete.id)
      notify('Салон и его объявления удалены.', 'success')
      setConfirmDelete(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось удалить салон.'), 'error')
    }
  }

  const q = search.trim().toLowerCase()
  const visible = q ? dealers.filter((d) => `${d.name} ${d.slug} ${d.phone}`.toLowerCase().includes(q)) : dealers
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const currentLogo = logoPreview || resolveMediaUrl(editing?.logo_url)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Автосалоны"
        description="Только эти салоны могут публиковать объявления на платформе."
        action={<button className="button button--primary" type="button" onClick={() => open(null)}><Plus size={17} /> Добавить салон</button>}
      />

      <div className="admin-toolbar">
        <div className="admin-search-form">
          <Search size={18} />
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Название, slug или телефон" aria-label="Поиск салонов" />
        </div>
      </div>

      {loading ? <LoadingState label="Загружаем салоны…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Салон</th><th>Контакты</th><th>Авто</th><th>Менеджеры</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>
              {visible.map((d) => (
                <tr key={d.id}>
                  <td>
                    <div className="dealer-car-cell">
                      <span className="dealer-panel-logo">{d.logo_url ? <img src={resolveMediaUrl(d.logo_url)} alt="" /> : <Building2 size={18} />}</span>
                      <span><Link to={`/dealers/${d.slug}`} target="_blank"><strong>{d.name}</strong></Link><small>{d.slug}{d.city_name ? ` · ${d.city_name}` : ''}</small></span>
                    </div>
                  </td>
                  <td>{d.phone || '—'}{d.whatsapp ? <><br /><small>WA: {d.whatsapp}</small></> : null}</td>
                  <td><Link className="text-link" to={`/admin/cars?dealer=${encodeURIComponent(d.slug)}`}>{d.car_count || 0}</Link></td>
                  <td><Link className="text-link" to={`/admin/managers?dealer=${d.id}`}>{d.managers_count || 0}</Link></td>
                  <td><span className={`admin-status ${d.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{d.is_active ? 'Активен' : 'Отключён'}</span></td>
                  <td>
                    <div className="table-actions">
                      <button className="icon-action" type="button" onClick={() => open(d)} title="Изменить" aria-label="Изменить"><Edit3 size={16} /></button>
                      <button className={`icon-action ${d.is_active ? 'icon-action--danger' : ''}`} type="button" onClick={() => toggle(d)} title={d.is_active ? 'Отключить' : 'Включить'} aria-label={d.is_active ? 'Отключить' : 'Включить'}><Power size={16} /></button>
                      <button className="icon-action icon-action--danger" type="button" onClick={() => setConfirmDelete(d)} title="Удалить" aria-label="Удалить"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visible.length && <div className="admin-empty">{q ? 'Ничего не найдено.' : 'Салоны ещё не добавлены.'}</div>}
        </div>
      )}

      {editing && (
        <div className="admin-modal-backdrop" role="presentation">
          <form className="admin-modal admin-modal--wide" role="dialog" aria-modal="true" aria-labelledby="dealer-form-title" onSubmit={save}>
            <h2 id="dealer-form-title">{editing.id ? 'Редактировать салон' : 'Новый автосалон'}</h2>
            <div className="dealer-profile-logo-row">
              <span className="dealer-panel-logo dealer-panel-logo--lg">{currentLogo ? <img src={currentLogo} alt="Логотип" /> : <Building2 size={26} />}</span>
              <label className="button button--outline"><ImagePlus size={16} /> Логотип<input type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={pickLogo} /></label>
            </div>
            <div className="form-grid">
              <label className="field-label">Название *<input required maxLength="200" value={form.name} onChange={set('name')} /></label>
              <label className="field-label">Slug (адрес страницы)<input value={form.slug} onChange={set('slug')} placeholder="создастся из названия" pattern="[a-z0-9]+(-[a-z0-9]+)*" title="латиница, цифры и дефис" /></label>
              <label className="field-label">Телефон<input type="tel" maxLength="20" value={form.phone} onChange={set('phone')} placeholder="+996700123456" /></label>
              <label className="field-label">WhatsApp<input type="tel" maxLength="20" value={form.whatsapp} onChange={set('whatsapp')} placeholder="+996700123456" /></label>
              <label className="field-label">Город<select value={form.city || ''} onChange={set('city')}><option value="">Не указан</option>{cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
              <label className="field-label">Адрес<input maxLength="300" value={form.address} onChange={set('address')} /></label>
            </div>
            <label className="field-label">Описание<textarea rows={3} value={form.description} onChange={set('description')} /></label>
            <label className="checkbox-label"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Салон активен</label>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setEditing(null)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
            </div>
          </form>
        </div>
      )}

      {confirmDelete && (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="dealer-delete-title">
            <h2 id="dealer-delete-title">Удалить «{confirmDelete.name}»?</h2>
            <p>Будут безвозвратно удалены все объявления салона ({confirmDelete.car_count || 0}) и их фотографии. Менеджеры потеряют доступ. Если нужно временно закрыть салон — используйте «Отключить».</p>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setConfirmDelete(null)}>Отмена</button>
              <button type="button" className="button button--danger" onClick={remove}>Удалить навсегда</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
