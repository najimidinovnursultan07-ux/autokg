import { useEffect, useMemo, useState } from 'react'
import { Building2, ExternalLink, ImagePlus, Landmark, LoaderCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getLookups } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { getDealerProfile, updateDealerProfile } from '../api/dealers.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import LocationPicker from '../components/dealers/LocationPicker.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const FIELDS = [
  'name', 'description', 'phone', 'whatsapp', 'address', 'city', 'latitude', 'longitude',
  'murabaha_enabled', 'murabaha_markup_percent', 'murabaha_min_down_percent', 'murabaha_max_term_months', 'murabaha_note',
]
const MAX_LOGO = 5 * 1024 * 1024

export default function DealerProfilePage() {
  const { refreshUser } = useAuth()
  const { notify } = useToast()
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({})
  const [cities, setCities] = useState([])
  const [logoFile, setLogoFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const logoPreview = useMemo(() => (logoFile ? URL.createObjectURL(logoFile) : ''), [logoFile])
  useEffect(() => () => logoPreview && URL.revokeObjectURL(logoPreview), [logoPreview])

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [data, lookups] = await Promise.all([getDealerProfile(), getLookups()])
      setProfile(data)
      setCities(lookups.cities)
      setForm(Object.fromEntries(FIELDS.map((key) => [key, data[key] ?? ''])))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить профиль салона.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

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
      FIELDS.forEach((key) => payload.append(key, form[key] ?? ''))
      if (logoFile) payload.append('logo', logoFile)
      const data = await updateDealerProfile(payload)
      setProfile(data)
      setLogoFile(null)
      await refreshUser()
      notify('Профиль салона сохранён.', 'success')
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сохранить профиль.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingState label="Загружаем профиль…" />
  if (error) return <ErrorState message={error} onRetry={load} />

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const logo = logoPreview || resolveMediaUrl(profile.logo_url)

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Кабинет салона"
        title="Профиль салона"
        description="Эти данные видят покупатели на странице салона и в объявлениях."
        action={<Link className="button button--outline" to={`/dealers/${profile.slug}`} target="_blank"><ExternalLink size={16} /> Страница салона</Link>}
      />
      <form className="listing-form" onSubmit={save}>
        <section className="form-section">
          <div className="dealer-profile-logo-row">
            <span className="dealer-panel-logo dealer-panel-logo--lg">
              {logo ? <img src={logo} alt="Логотип" /> : <Building2 size={28} />}
            </span>
            <label className="button button--outline">
              <ImagePlus size={16} /> {logo ? 'Заменить логотип' : 'Загрузить логотип'}
              <input type="file" hidden accept="image/jpeg,image/png,image/webp" onChange={pickLogo} />
            </label>
          </div>
          <div className="form-grid">
            <label className="field-label">Название<input required maxLength="200" value={form.name} onChange={set('name')} /></label>
            <label className="field-label">Город<select value={form.city || ''} onChange={set('city')}><option value="">Не указан</option>{cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
            <label className="field-label">Телефон<input type="tel" maxLength="20" value={form.phone} onChange={set('phone')} placeholder="+996700123456" /></label>
            <label className="field-label">WhatsApp<input type="tel" maxLength="20" value={form.whatsapp} onChange={set('whatsapp')} placeholder="+996700123456" /></label>
          </div>
          <label className="field-label">Адрес<input maxLength="300" value={form.address} onChange={set('address')} placeholder="г. Бишкек, ул. …" /></label>
          <LocationPicker
            latitude={form.latitude}
            longitude={form.longitude}
            onChange={(latitude, longitude) => setForm((current) => ({ ...current, latitude, longitude }))}
          />
          <label className="field-label">Описание<textarea rows="4" value={form.description} onChange={set('description')} placeholder="Расскажите о салоне: опыт, гарантии, услуги…" /></label>
        </section>
        <section className="form-section">
          <div className="form-section-heading"><span><Landmark size={15} /></span><div><h2>Мурабаха</h2><p>Покупка в рассрочку без процентов: фиксированная наценка, известная заранее. Покупатели увидят калькулятор платежа на страницах ваших автомобилей.</p></div></div>
          <label className="checkbox-label">
            <input type="checkbox" checked={Boolean(form.murabaha_enabled)} onChange={(e) => setForm({ ...form, murabaha_enabled: e.target.checked })} />
            Салон продаёт автомобили по мурабахе
          </label>
          {form.murabaha_enabled && <>
            <div className="form-grid">
              <label className="field-label">Наценка, % в год<input type="number" required min="0" max="100" step="0.1" value={form.murabaha_markup_percent} onChange={set('murabaha_markup_percent')} placeholder="12" /></label>
              <label className="field-label">Минимальный первый взнос, %<input type="number" required min="0" max="90" step="1" value={form.murabaha_min_down_percent} onChange={set('murabaha_min_down_percent')} placeholder="30" /></label>
              <label className="field-label">Максимальный срок, мес.<input type="number" required min="3" max="120" step="1" value={form.murabaha_max_term_months} onChange={set('murabaha_max_term_months')} placeholder="24" /></label>
            </div>
            <label className="field-label">Примечание для покупателей<input maxLength="300" value={form.murabaha_note} onChange={set('murabaha_note')} placeholder="Например: без поручителей, оформление за 1 день" /></label>
          </>}
        </section>
        <div className="form-actions">
          <button className="button button--primary" type="submit" disabled={saving}>{saving && <LoaderCircle className="spin" size={16} />} Сохранить</button>
        </div>
      </form>
    </section>
  )
}
