import { useCallback, useEffect, useMemo, useState } from 'react'
import { BarChart3, Download, Edit3, ExternalLink, ImagePlus, Megaphone, Play, Plus, Power, Trash2 } from 'lucide-react'
import {
  AD_PLACEMENTS, createAdminAd, deleteAdminAd, downloadAdminAdStats,
  getAdminAdStats, getAdminAds, updateAdminAd,
} from '../api/ads.js'
import { resolveMediaUrl } from '../api/client.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const MAX_IMAGE = 5 * 1024 * 1024
const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const emptyForm = {
  title: '', advertiser: '', advertiser_contact: '', placement: 'home_top', link_url: '',
  starts_on: '', ends_on: '', priority: 1, is_active: true,
}

const placementLabel = Object.fromEntries(AD_PLACEMENTS.map((p) => [p.value, p.label]))
const formatDay = (value) => (value ? new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU') : '')
const formatNumber = (value) => new Intl.NumberFormat('ru-RU').format(value || 0)

function todayIso() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}

function bannerStatus(ad) {
  const today = todayIso()
  if (!ad.is_active) return ['Выключен', 'inactive']
  if (ad.ends_on && ad.ends_on < today) return ['Завершён', 'sold']
  if (ad.starts_on && ad.starts_on > today) return ['Запланирован', 'pending']
  return ['Показывается', 'active']
}

function useObjectUrl(file) {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : ''), [file])
  useEffect(() => () => url && URL.revokeObjectURL(url), [url])
  return url
}

export default function AdminAdsPage() {
  const { notify } = useToast()
  const [ads, setAds] = useState([])
  const [placementFilter, setPlacementFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null) // null — закрыто, {} — новый, ad — правка
  const [form, setForm] = useState(emptyForm)
  const [imageFile, setImageFile] = useState(null)
  const [mobileFile, setMobileFile] = useState(null)
  const [removeMobile, setRemoveMobile] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [statsFor, setStatsFor] = useState(null)

  const imagePreview = useObjectUrl(imageFile)
  const mobilePreview = useObjectUrl(mobileFile)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setAds(await getAdminAds())
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить рекламу.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const open = (ad) => {
    setEditing(ad || {})
    setImageFile(null)
    setMobileFile(null)
    setRemoveMobile(false)
    setForm(ad ? Object.fromEntries(Object.keys(emptyForm).map((k) => [k, ad[k] ?? emptyForm[k]])) : emptyForm)
  }

  const pickImage = (setter) => (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!IMAGE_TYPES.includes(file.type)) return notify('Картинка: только JPG, PNG или WEBP.', 'error')
    if (file.size > MAX_IMAGE) return notify('Картинка: не более 5 МБ.', 'error')
    setter(file)
  }

  const save = async (event) => {
    event.preventDefault()
    if (!editing.id && !imageFile) return notify('Загрузите картинку баннера.', 'error')
    setSaving(true)
    try {
      const payload = new FormData()
      Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ''))
      if (imageFile) payload.append('image', imageFile)
      if (mobileFile) payload.append('mobile_image', mobileFile)
      else if (removeMobile) payload.append('remove_mobile_image', 'true')
      if (editing.id) await updateAdminAd(editing.id, payload)
      else await createAdminAd(payload)
      notify(editing.id ? 'Баннер обновлён.' : 'Баннер добавлен.', 'success')
      setEditing(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сохранить баннер.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const launchNow = async (ad) => {
    try {
      await updateAdminAd(ad.id, { starts_on: todayIso(), is_active: true })
      notify('Баннер запущен — он уже показывается на сайте.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось запустить баннер.'), 'error')
    }
  }

  const toggle = async (ad) => {
    try {
      await updateAdminAd(ad.id, { is_active: !ad.is_active })
      notify(ad.is_active ? 'Баннер выключен.' : 'Баннер включён.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить баннер.'), 'error')
    }
  }

  const remove = async () => {
    try {
      await deleteAdminAd(confirmDelete.id)
      notify('Баннер удалён.', 'success')
      setConfirmDelete(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось удалить баннер.'), 'error')
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const visible = placementFilter ? ads.filter((ad) => ad.placement === placementFilter) : ads
  const sizeHint = AD_PLACEMENTS.find((p) => p.value === form.placement)?.size
  const currentImage = imagePreview || resolveMediaUrl(editing?.image_url)
  const currentMobile = mobilePreview || (removeMobile ? '' : resolveMediaUrl(editing?.mobile_image_url))

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Реклама"
        description="Баннеры партнёров: банки, страховые, автосервисы и другие компании. Показы и клики считаются автоматически."
        action={<button className="button button--primary" type="button" onClick={() => open(null)}><Plus size={17} /> Добавить баннер</button>}
      />

      <div className="admin-toolbar">
        <label className="field-label ads-filter">Место показа
          <select value={placementFilter} onChange={(e) => setPlacementFilter(e.target.value)}>
            <option value="">Все места</option>
            {AD_PLACEMENTS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </label>
      </div>

      {loading ? <LoadingState label="Загружаем рекламу…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <div className="admin-table-wrap">
          <table className="admin-table admin-table--cards ads-table">
            <thead><tr><th>Баннер</th><th>Место</th><th>Период</th><th>Статус</th><th>Показы</th><th>Клики</th><th>CTR</th><th>Действия</th></tr></thead>
            <tbody>
              {visible.map((ad) => {
                const [label, tone] = bannerStatus(ad)
                return (
                  <tr key={ad.id}>
                    <td className="admin-card-head">
                      <div className="dealer-car-cell">
                        <span className="ad-thumb"><img src={resolveMediaUrl(ad.image_url)} alt="" /></span>
                        <span><strong>{ad.title}</strong><small>{ad.advertiser}{ad.advertiser_contact ? ` · ${ad.advertiser_contact}` : ''}</small></span>
                      </div>
                    </td>
                    <td data-label="Место">{placementLabel[ad.placement] || ad.placement}</td>
                    <td data-label="Период">{ad.starts_on || ad.ends_on ? `${formatDay(ad.starts_on) || '…'} — ${formatDay(ad.ends_on) || 'без срока'}` : 'Без срока'}</td>
                    <td data-label="Статус">
                      <div className="ad-status-cell">
                        <span className={`admin-status admin-status--${tone}`}>{label}</span>
                        {label === 'Запланирован' && (
                          <>
                            <small>Начнётся {formatDay(ad.starts_on)}</small>
                            <button type="button" className="ad-launch-button" onClick={() => launchNow(ad)}><Play size={13} /> Запустить сейчас</button>
                          </>
                        )}
                      </div>
                    </td>
                    <td data-label="Показы">{formatNumber(ad.impressions)}</td>
                    <td data-label="Клики">{formatNumber(ad.clicks)}</td>
                    <td data-label="CTR">{ad.ctr}%</td>
                    <td data-label="Действия">
                      <div className="table-actions ads-actions">
                        <button className="icon-action" type="button" onClick={() => setStatsFor(ad)} title="Статистика" aria-label="Статистика"><BarChart3 size={16} /></button>
                        <a className="icon-action" href={ad.link_url} target="_blank" rel="noopener noreferrer" title="Открыть ссылку" aria-label="Открыть ссылку"><ExternalLink size={16} /></a>
                        <button className="icon-action" type="button" onClick={() => open(ad)} title="Изменить" aria-label="Изменить"><Edit3 size={16} /></button>
                        <button className={`icon-action ${ad.is_active ? 'icon-action--danger' : ''}`} type="button" onClick={() => toggle(ad)} title={ad.is_active ? 'Выключить' : 'Включить'} aria-label={ad.is_active ? 'Выключить' : 'Включить'}><Power size={16} /></button>
                        <button className="icon-action icon-action--danger" type="button" onClick={() => setConfirmDelete(ad)} title="Удалить" aria-label="Удалить"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!visible.length && (
            <div className="admin-empty">
              <Megaphone size={22} />
              <p>{placementFilter ? 'В этом месте баннеров нет.' : 'Баннеров пока нет. Добавьте первого рекламодателя.'}</p>
            </div>
          )}
        </div>
      )}

      {editing && (
        <div className="admin-modal-backdrop" role="presentation">
          <form className="admin-modal admin-modal--wide" role="dialog" aria-modal="true" aria-labelledby="ad-form-title" onSubmit={save}>
            <h2 id="ad-form-title">{editing.id ? 'Редактировать баннер' : 'Новый баннер'}</h2>
            <div className="form-grid">
              <label className="field-label">Рекламодатель *<input required maxLength="120" value={form.advertiser} onChange={set('advertiser')} placeholder="Банк, страховая, автосервис…" /></label>
              <label className="field-label">Контакт рекламодателя<input maxLength="120" value={form.advertiser_contact} onChange={set('advertiser_contact')} placeholder="Имя, телефон — видно только вам" /></label>
              <label className="field-label">Название баннера *<input required maxLength="120" value={form.title} onChange={set('title')} placeholder="Автокредит от 14% годовых" /></label>
              <label className="field-label">Ссылка *<input required type="url" maxLength="500" value={form.link_url} onChange={set('link_url')} placeholder="https://…" /></label>
              <label className="field-label">Место показа *
                <select value={form.placement} onChange={set('placement')}>
                  {AD_PLACEMENTS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </label>
              <label className="field-label">Приоритет (1–10)<input type="number" min="1" max="10" value={form.priority} onChange={set('priority')} /></label>
              <label className="field-label">Показывать с<input type="date" value={form.starts_on || ''} onChange={set('starts_on')} /></label>
              <label className="field-label">Показывать по<input type="date" min={form.starts_on || undefined} value={form.ends_on || ''} onChange={set('ends_on')} /></label>
            </div>
            <p className="field-hint">Рекомендуемый размер картинки: {sizeHint}. Пустые даты — без ограничения. Если в одном месте несколько баннеров, они чередуются; приоритет 3 показывается в 3 раза чаще, чем 1.</p>

            <div className="ad-upload-row">
              <div className="ad-upload">
                <span className="ad-upload-preview">{currentImage ? <img src={currentImage} alt="Баннер" /> : <ImagePlus size={24} />}</span>
                <label className="button button--outline"><ImagePlus size={16} /> {currentImage ? 'Заменить картинку' : 'Картинка *'}<input type="file" hidden accept={IMAGE_TYPES.join(',')} onChange={pickImage(setImageFile)} /></label>
              </div>
              <div className="ad-upload">
                <span className="ad-upload-preview ad-upload-preview--mobile">{currentMobile ? <img src={currentMobile} alt="Для телефона" /> : <ImagePlus size={22} />}</span>
                <span className="ad-upload-actions">
                  <label className="button button--outline"><ImagePlus size={16} /> Для телефона<input type="file" hidden accept={IMAGE_TYPES.join(',')} onChange={(e) => { setRemoveMobile(false); pickImage(setMobileFile)(e) }} /></label>
                  {currentMobile && <button type="button" className="filter-reset" onClick={() => { setMobileFile(null); setRemoveMobile(true) }}>Убрать</button>}
                </span>
              </div>
            </div>

            <label className="checkbox-label"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Баннер включён</label>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setEditing(null)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
            </div>
          </form>
        </div>
      )}

      {statsFor && <AdStatsModal ad={statsFor} onClose={() => setStatsFor(null)} />}

      {confirmDelete && (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="ad-delete-title">
            <h2 id="ad-delete-title">Удалить баннер «{confirmDelete.title}»?</h2>
            <p>Вместе с баннером удалится его статистика. Если реклама просто закончилась — лучше выключите баннер, чтобы сохранить отчёт.</p>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setConfirmDelete(null)}>Отмена</button>
              <button type="button" className="button button--danger" onClick={remove}>Удалить</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function AdStatsModal({ ad, onClose }) {
  const { notify } = useToast()
  const [period, setPeriod] = useState({ from: '', to: '' })
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async (params) => {
    setError('')
    try {
      const data = await getAdminAdStats(ad.id, params)
      setStats(data)
      setPeriod({ from: data.period.from, to: data.period.to })
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить статистику.'))
    }
  }, [ad.id])

  useEffect(() => { load({}) }, [load])

  const apply = (event) => {
    event.preventDefault()
    load(period)
  }

  const download = async () => {
    try {
      await downloadAdminAdStats(ad.id, period)
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось скачать отчёт.'), 'error')
    }
  }

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <div className="admin-modal admin-modal--wide" role="dialog" aria-modal="true" aria-labelledby="ad-stats-title">
        <h2 id="ad-stats-title">Статистика: {ad.title}</h2>
        <p className="field-hint">{ad.advertiser} · {placementLabel[ad.placement]}</p>
        <form className="ad-stats-period" onSubmit={apply}>
          <label className="field-label">С<input type="date" value={period.from} onChange={(e) => setPeriod({ ...period, from: e.target.value })} /></label>
          <label className="field-label">По<input type="date" value={period.to} onChange={(e) => setPeriod({ ...period, to: e.target.value })} /></label>
          <button type="submit" className="button button--outline">Показать</button>
          <button type="button" className="button button--primary" onClick={download} disabled={!stats}><Download size={16} /> Excel для рекламодателя</button>
        </form>

        {error ? <ErrorState message={error} onRetry={() => load(period)} /> : !stats ? <LoadingState compact label="Считаем…" /> : (
          <>
            <div className="ad-stats-totals">
              <div><span>Показы</span><strong>{formatNumber(stats.totals.impressions)}</strong></div>
              <div><span>Клики</span><strong>{formatNumber(stats.totals.clicks)}</strong></div>
              <div><span>CTR</span><strong>{stats.totals.ctr}%</strong></div>
            </div>
            {stats.days.length ? (
              <div className="admin-table-wrap ad-stats-days">
                <table className="admin-table">
                  <thead><tr><th>День</th><th>Показы</th><th>Клики</th><th>CTR</th></tr></thead>
                  <tbody>
                    {[...stats.days].reverse().map((row) => (
                      <tr key={row.date}><td>{formatDay(row.date)}</td><td>{formatNumber(row.impressions)}</td><td>{formatNumber(row.clicks)}</td><td>{row.ctr}%</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="field-hint">За этот период показов не было.</p>}
          </>
        )}
        <div className="admin-modal-actions">
          <button type="button" className="button button--secondary" onClick={onClose}>Закрыть</button>
        </div>
      </div>
    </div>
  )
}
