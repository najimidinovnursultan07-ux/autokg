import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Check, EyeOff, ImagePlus, LoaderCircle, Star, Trash2 } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  deleteCarPhoto,
  getDashboardCar,
  getLookups,
  saveDashboardCar,
  setMainCarPhoto,
  uploadCarPhotos,
} from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage, getFieldErrors } from '../utils/errors.js'
import { formatDate } from '../utils/format.js'
import { DEFAULT_LISTING_DAYS, LISTING_DURATIONS } from '../utils/listing.js'

const MAX_YEAR = new Date().getFullYear() + 1
const MIN_YEAR = 1980
const MAX_PHOTOS = 15
const MAX_FILE_SIZE = 5 * 1024 * 1024
const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const initialForm = {
  model: '',
  city: '',
  year: '',
  price: '',
  currency: 'KGS',
  mileage: '',
  engine_volume: '',
  engine_type: 'petrol',
  transmission: 'automatic',
  drive_type: 'fwd',
  body_type: 'sedan',
  condition: 'used',
  color: '',
  murabaha_available: false,
  description: '',
  contact_phone: '',
}

const choiceLabels = {
  engine_type: [['petrol', 'Бензин'], ['diesel', 'Дизель'], ['hybrid', 'Гибрид'], ['electric', 'Электро'], ['lpg', 'Газ'], ['other', 'Другое']],
  transmission: [['manual', 'Механическая'], ['automatic', 'Автоматическая'], ['cvt', 'Вариатор'], ['robotic', 'Робот']],
  drive_type: [['fwd', 'Передний'], ['rwd', 'Задний'], ['awd', 'Полный']],
  body_type: [['sedan', 'Седан'], ['hatchback', 'Хэтчбек'], ['suv', 'Внедорожник'], ['wagon', 'Универсал'], ['coupe', 'Купе'], ['minivan', 'Минивэн'], ['pickup', 'Пикап'], ['other', 'Другое']],
  condition: [['new', 'Новый'], ['used', 'С пробегом'], ['damaged', 'Требует ремонта']],
}

export default function CarFormPage() {
  const { id } = useParams()
  const isEditing = Boolean(id)
  const navigate = useNavigate()
  const { notify } = useToast()
  const [form, setForm] = useState(initialForm)
  const [carStatus, setCarStatus] = useState('active')
  // Срок размещения: при создании — 30 дней, при редактировании '' — не менять
  const [duration, setDuration] = useState(isEditing ? '' : String(DEFAULT_LISTING_DAYS))
  const [currentExpiry, setCurrentExpiry] = useState(null)
  const [lookups, setLookups] = useState({ brands: [], models: [], cities: [] })
  const [selectedBrandId, setSelectedBrandId] = useState('')
  const [existingImages, setExistingImages] = useState([])
  const [newImages, setNewImages] = useState([])
  const [newCoverFile, setNewCoverFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [loadError, setLoadError] = useState('')
  const [carId, setCarId] = useState(id || null)

  const previews = useMemo(
    () => newImages.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [newImages],
  )
  useEffect(() => () => previews.forEach(({ url }) => URL.revokeObjectURL(url)), [previews])

  useEffect(() => {
    let active = true
    const loadForm = async () => {
      try {
        const [catalog, car] = await Promise.all([
          getLookups(),
          isEditing ? getDashboardCar(id) : Promise.resolve(null),
        ])
        if (!active) return
        setLookups(catalog)
        if (car) {
          setCarId(car.id)
          setCarStatus(car.status)
          setCurrentExpiry({ expires_at: car.expires_at, is_expired: car.is_expired })
          setSelectedBrandId(String(catalog.models.find((m) => m.id === car.model)?.brand || ''))
          setForm({
            model: String(car.model),
            city: String(car.city),
            year: String(car.year),
            price: String(Math.round(Number(car.price))),
            currency: car.currency || 'KGS',
            mileage: String(car.mileage),
            engine_volume: car.engine_volume || '',
            engine_type: car.engine_type,
            transmission: car.transmission,
            drive_type: car.drive_type,
            body_type: car.body_type,
            condition: car.condition,
            color: car.color || '',
            murabaha_available: Boolean(car.murabaha_available),
            description: car.description,
            contact_phone: car.contact_phone,
          })
          setExistingImages(car.images || [])
        }
      } catch (requestError) {
        if (active) setLoadError(getErrorMessage(requestError, 'Не удалось загрузить объявление.'))
      } finally {
        if (active) setLoading(false)
      }
    }
    loadForm()
    return () => { active = false }
  }, [id, isEditing])

  const update = (key) => (event) => setForm((value) => ({ ...value, [key]: event.target.value }))

  const addFiles = (event) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    const valid = []
    for (const file of files) {
      if (!IMAGE_TYPES.includes(file.type)) notify(`${file.name}: разрешены только JPG, PNG и WEBP.`, 'error')
      else if (file.size > MAX_FILE_SIZE) notify(`${file.name}: размер не должен превышать 5 МБ.`, 'error')
      else valid.push(file)
    }
    const available = MAX_PHOTOS - existingImages.length - newImages.length
    if (valid.length > available) notify(`Можно добавить ещё не более ${Math.max(available, 0)} фото (максимум ${MAX_PHOTOS}).`, 'error')
    setNewImages((current) => [...current, ...valid.slice(0, Math.max(available, 0))])
  }

  const removeNewImage = (file) => {
    setNewImages((items) => items.filter((item) => item !== file))
    if (file === newCoverFile) setNewCoverFile(null)
  }

  const chooseCover = async (image) => {
    try {
      await setMainCarPhoto(carId, image.id)
      setNewCoverFile(null)
      setExistingImages((items) => items.map((item) => ({ ...item, is_cover: item.id === image.id })))
      notify('Главное фото изменено.', 'success')
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось изменить главное фото.'), 'error')
    }
  }

  const removeImage = async (image) => {
    if (!window.confirm('Удалить эту фотографию?')) return
    try {
      await deleteCarPhoto(carId, image.id)
      setExistingImages((items) => {
        const remaining = items.filter((item) => item.id !== image.id)
        return image.is_cover && remaining.length
          ? remaining.map((item, index) => ({ ...item, is_cover: index === 0 }))
          : remaining
      })
      notify('Фотография удалена.', 'success')
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось удалить фотографию.'), 'error')
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    const status = event.nativeEvent.submitter?.value === 'hidden' ? 'hidden' : (isEditing && carStatus === 'sold' ? 'sold' : 'active')
    setSaving(true)
    setError('')
    setFieldErrors({})
    let savedId = carId
    try {
      const payload = {
        ...form,
        model: Number(form.model),
        city: Number(form.city),
        year: Number(form.year),
        mileage: Number(form.mileage || 0),
        engine_volume: form.engine_volume || null,
        status,
      }
      if (duration !== '') payload.duration_days = Number(duration)
      const car = await saveDashboardCar(payload, carId)
      savedId = car.id
      setCarId(car.id)
      if (newImages.length) {
        const uploaded = await uploadCarPhotos(car.id, newImages)
        const coverIndex = newImages.indexOf(newCoverFile)
        if (coverIndex >= 0 && uploaded[coverIndex]) await setMainCarPhoto(car.id, uploaded[coverIndex].id)
      }
      notify(status === 'hidden' ? 'Объявление сохранено (скрыто с сайта).' : 'Объявление сохранено и опубликовано.', 'success')
      navigate('/dashboard')
    } catch (requestError) {
      setFieldErrors(getFieldErrors(requestError))
      setError(getErrorMessage(requestError, 'Не удалось сохранить объявление.'))
      // Машина уже создана, но фото не загрузились — переходим в режим редактирования
      if (!isEditing && savedId) navigate(`/dashboard/cars/${savedId}/edit`, { replace: true })
    } finally {
      setSaving(false)
    }
  }

  const availableModels = lookups.models.filter((m) => !selectedBrandId || String(m.brand) === selectedBrandId)
  const fieldError = (key) => fieldErrors[key]?.[0] && <small className="field-error">{fieldErrors[key][0]}</small>

  if (loading) return <LoadingState label="Загружаем форму…" />
  if (loadError) return <ErrorState message={loadError} onRetry={() => window.location.reload()} />

  return (
    <section className="account-page car-form-page">
      <Link to="/dashboard" className="back-link"><ArrowLeft size={17} /> К объявлениям</Link>
      <PageTitle eyebrow="Кабинет салона" title={isEditing ? 'Редактировать объявление' : 'Добавить автомобиль'} description="Заполните характеристики и добавьте фотографии автомобиля." />
      {error && <div className="form-alert" role="alert">{error}</div>}
      <form className="listing-form" onSubmit={submit}>
        <section className="form-section">
          <div className="form-section-heading"><span>01</span><div><h2>Основная информация</h2><p>Марка, модель и расположение автомобиля.</p></div></div>
          <div className="form-grid">
            <label className="field-label">Марка<select value={selectedBrandId} onChange={(e) => { setSelectedBrandId(e.target.value); setForm((c) => ({ ...c, model: '' })) }} required><option value="">Выберите марку</option>{lookups.brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>
            <label className="field-label">Модель<select value={form.model} onChange={update('model')} required><option value="">Выберите модель</option>{availableModels.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select>{fieldError('model')}</label>
            <label className="field-label">Город<select value={form.city} onChange={update('city')} required><option value="">Выберите город</option>{lookups.cities.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
            <label className="field-label">Год выпуска<input type="number" min={MIN_YEAR} max={MAX_YEAR} required value={form.year} onChange={update('year')} placeholder="Например, 2020" />{fieldError('year')}</label>
            <label className="field-label">Срок размещения на сайте
              <select value={duration} onChange={(e) => setDuration(e.target.value)}>
                {isEditing && (
                  <option value="">
                    {currentExpiry?.is_expired
                      ? 'Срок истёк — при публикации 30 дней'
                      : currentExpiry?.expires_at ? `Не менять (до ${formatDate(currentExpiry.expires_at)})` : 'Не менять (без срока)'}
                  </option>
                )}
                {LISTING_DURATIONS.map(([days, label]) => (
                  <option key={days} value={days}>{isEditing && days ? `Продлить: ${label} с сегодня` : label}</option>
                ))}
              </select>
              <small>После окончания срока объявление скроется с сайта, но останется в кабинете — его можно продлить.</small>
              {fieldError('duration_days')}
            </label>
          </div>
        </section>

        <section className="form-section">
          <div className="form-section-heading"><span>02</span><div><h2>Цена и характеристики</h2><p>Помогите покупателю понять, подходит ли ему автомобиль.</p></div></div>
          <div className="form-grid">
            <label className="field-label">Цена<span className="field-range"><input type="number" min="1" step="1" required value={form.price} onChange={update('price')} placeholder="1 250 000" /><select value={form.currency} onChange={update('currency')} aria-label="Валюта"><option value="KGS">сом</option><option value="USD">$</option></select></span>{fieldError('price')}</label>
            <label className="field-label">Пробег, км<input type="number" min="0" required value={form.mileage} onChange={update('mileage')} placeholder="85 000" /></label>
            <label className="field-label">Топливо<select value={form.engine_type} onChange={update('engine_type')}>{choiceLabels.engine_type.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field-label">Объём двигателя, л<input type="number" min="0.1" max="99.9" step="0.1" value={form.engine_volume} onChange={update('engine_volume')} placeholder="2.0" /></label>
            <label className="field-label">Коробка передач<select value={form.transmission} onChange={update('transmission')}>{choiceLabels.transmission.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field-label">Привод<select value={form.drive_type} onChange={update('drive_type')}>{choiceLabels.drive_type.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field-label">Тип кузова<select value={form.body_type} onChange={update('body_type')}>{choiceLabels.body_type.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field-label">Состояние<select value={form.condition} onChange={update('condition')}>{choiceLabels.condition.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="field-label">Цвет<input maxLength="50" value={form.color} onChange={update('color')} placeholder="Белый" /></label>
            <label className="field-label">Телефон для связи<input type="tel" value={form.contact_phone} onChange={update('contact_phone')} placeholder="По умолчанию — телефон салона" />{fieldError('contact_phone')}</label>
          </div>
          <label className="checkbox-label">
            <input type="checkbox" checked={form.murabaha_available} onChange={(e) => setForm((value) => ({ ...value, murabaha_available: e.target.checked }))} />
            Доступна покупка по мурабахе
          </label>
          <p className="field-hint">Покупатель увидит калькулятор платежа. Наценку, взнос и срок задайте в разделе <Link className="text-link" to="/dashboard/murabaha">«Мурабаха»</Link>.</p>
          <label className="field-label">Описание<textarea rows="5" maxLength="10000" required value={form.description} onChange={update('description')} placeholder="Состояние, комплектация, история обслуживания…" /><small>{form.description.length} / 10 000</small></label>
        </section>

        <section className="form-section">
          <div className="form-section-heading"><span>03</span><div><h2>Фотографии</h2><p>До {MAX_PHOTOS} фото: JPG, PNG или WEBP, до 5 МБ каждое.</p></div></div>
          <label className="upload-zone">
            <ImagePlus size={25} />
            <strong>Выберите фотографии</strong>
            <span>Можно выбрать несколько файлов сразу</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={addFiles} />
          </label>
          {(existingImages.length > 0 || previews.length > 0) && (
            <div className="form-photo-grid">
              {existingImages.map((image, index) => (
                <div className="form-photo" key={image.id}>
                  <img src={resolveMediaUrl(image.thumb || image.image)} alt={`Фото ${index + 1}`} />
                  {image.is_cover && <span className="cover-tag"><Star size={12} fill="currentColor" /> Главное</span>}
                  <div className="photo-controls">
                    {!image.is_cover && <button type="button" onClick={() => chooseCover(image)} aria-label="Сделать главным" title="Сделать главным"><Star size={15} /></button>}
                    <button type="button" onClick={() => removeImage(image)} aria-label="Удалить фото" title="Удалить"><Trash2 size={15} /></button>
                  </div>
                </div>
              ))}
              {previews.map(({ file, url }) => (
                <div className="form-photo form-photo--new" key={`${file.name}-${file.lastModified}-${file.size}`}>
                  <img src={url} alt={file.name} />
                  {newCoverFile === file && <span className="cover-tag"><Star size={12} fill="currentColor" /> Главное</span>}
                  <span className="new-photo-tag">Новое</span>
                  <div className="photo-controls">
                    <button type="button" onClick={() => setNewCoverFile(file)} aria-label="Сделать главным" title="Сделать главным"><Star size={15} /></button>
                    <button type="button" onClick={() => removeNewImage(file)} aria-label="Убрать фото" title="Убрать"><Trash2 size={15} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="field-hint">Фото: {existingImages.length + newImages.length} / {MAX_PHOTOS}. Если главное фото не выбрано, им станет первое.</p>
        </section>

        <div className="form-actions">
          <Link className="button button--outline" to="/dashboard">Отмена</Link>
          <button className="button button--outline" type="submit" value="hidden" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16} /> : <EyeOff size={16} />} Сохранить скрытым</button>
          <button className="button button--primary" type="submit" value="active" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16} /> : <Check size={17} />} {carStatus === 'sold' && isEditing ? 'Сохранить' : 'Опубликовать'}</button>
        </div>
      </form>
    </section>
  )
}
