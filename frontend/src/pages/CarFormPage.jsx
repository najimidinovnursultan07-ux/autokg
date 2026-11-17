import { useEffect, useMemo, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowUp, Check, ImagePlus, LoaderCircle, Star, Trash2 } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  deleteCarImage,
  getCar,
  getLookups,
  reorderCarImages,
  saveCar,
  setCarCover,
  submitCar,
  uploadCarImages,
} from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const initialForm = {
  model: '',
  city: '',
  year: '',
  price: '',
  mileage: '',
  engine_volume: '',
  engine_type: 'petrol',
  transmission: 'automatic',
  drive_type: 'fwd',
  body_type: 'sedan',
  condition: 'used',
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
const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp']
const maxPhotos = 20
const maxFileSize = 10 * 1024 * 1024

export default function CarFormPage() {
  const { id } = useParams()
  const isEditing = Boolean(id)
  const navigate = useNavigate()
  const { user } = useAuth()
  const { notify } = useToast()
  const [form, setForm] = useState({ ...initialForm, contact_phone: user?.phone || '' })
  const [lookups, setLookups] = useState({ brands: [], models: [], cities: [] })
  const [selectedBrandId, setSelectedBrandId] = useState('')
  const [existingImages, setExistingImages] = useState([])
  const [newImages, setNewImages] = useState([])
  const [newCoverFile, setNewCoverFile] = useState(null)
  const [loading, setLoading] = useState(isEditing)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [carId, setCarId] = useState(id || null)
  const [previewUrls, setPreviewUrls] = useState([])

  const previews = useMemo(
    () => newImages.map((file) => ({ file, url: previewUrls[newImages.indexOf(file)] })),
    [newImages, previewUrls],
  )

  useEffect(() => {
    const urls = newImages.map((file) => URL.createObjectURL(file))
    setPreviewUrls(urls)
    return () => urls.forEach((url) => URL.revokeObjectURL(url))
  }, [newImages])

  useEffect(() => {
    let active = true
    const loadForm = async () => {
      try {
        const [catalog, car] = await Promise.all([
          getLookups(),
          isEditing ? getCar(id) : Promise.resolve(null),
        ])
        if (!active) return
        setLookups(catalog)
        if (car) {
          setCarId(car.id)
          setSelectedBrandId(
            String(catalog.models.find((model) => model.id === car.model)?.brand || ''),
          )
          setForm({
            model: String(car.model),
            city: String(car.city),
            year: String(car.year),
            price: String(car.price),
            mileage: String(car.mileage),
            engine_volume: car.engine_volume || '',
            engine_type: car.engine_type,
            transmission: car.transmission,
            drive_type: car.drive_type,
            body_type: car.body_type,
            condition: car.condition,
            description: car.description,
            contact_phone: car.contact_phone,
          })
          setExistingImages(car.images || [])
        }
      } catch (requestError) {
        if (active) {
          const message = getErrorMessage(requestError, 'Не удалось загрузить форму объявления.')
          setError(message)
          setLoadError(message)
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    loadForm()
    return () => {
      active = false
    }
  }, [id, isEditing])

  const update = (key) => (event) => setForm((value) => ({ ...value, [key]: event.target.value }))

  const addFiles = (event) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    const valid = []
    for (const file of files) {
      const extension = `.${file.name.split('.').pop()}`.toLowerCase()
      if (!imageExtensions.includes(extension)) {
        notify(`${file.name}: разрешены JPG, JPEG, PNG и WEBP.`, 'error')
      } else if (file.size > maxFileSize) {
        notify(`${file.name}: размер не должен превышать 10 МБ.`, 'error')
      } else {
        valid.push(file)
      }
    }
    const available = maxPhotos - existingImages.length - newImages.length
    if (valid.length > available) {
      notify(`Можно добавить не более ${Math.max(available, 0)} фотографий.`, 'error')
    }
    setNewImages((current) => [...current, ...valid.slice(0, Math.max(available, 0))])
  }

  const removeNewImage = (index) => {
    const removed = newImages[index]
    setNewImages((items) => items.filter((_, itemIndex) => itemIndex !== index))
    if (removed === newCoverFile) setNewCoverFile(null)
  }

  const moveImage = async (index, direction) => {
    const target = index + direction
    if (target < 0 || target >= existingImages.length) return
    const reordered = [...existingImages]
    ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
    setExistingImages(reordered)
    try {
      await reorderCarImages(carId, reordered.map((image) => image.id))
    } catch (requestError) {
      setExistingImages(existingImages)
      notify(getErrorMessage(requestError, 'Не удалось изменить порядок фотографий.'), 'error')
    }
  }

  const chooseCover = async (image) => {
    try {
      await setCarCover(carId, image.id)
      setNewCoverFile(null)
      setExistingImages((items) => items.map((item) => ({ ...item, is_cover: item.id === image.id })))
      notify('Главная фотография изменена.', 'success')
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось изменить обложку.'), 'error')
    }
  }

  const removeImage = async (image) => {
    try {
      await deleteCarImage(carId, image.id)
      setExistingImages((items) => {
        const remaining = items.filter((item) => item.id !== image.id)
        if (image.is_cover && remaining.length) {
          return remaining.map((item, index) => ({ ...item, is_cover: index === 0 }))
        }
        return remaining
      })
      notify('Фотография удалена.', 'success')
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось удалить фотографию.'), 'error')
    }
  }

  const submit = async (event, sendForReview = false) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        model: Number(form.model),
        city: Number(form.city),
        year: Number(form.year),
        mileage: Number(form.mileage || 0),
        engine_volume: form.engine_volume || null,
      }
      const car = await saveCar(payload, carId)
      setCarId(car.id)
      if (newImages.length) {
        await uploadCarImages(car.id, newImages, async (batchImages, batchFiles) => {
          const coverIndex = batchFiles.indexOf(newCoverFile)
          const selectedCoverId = coverIndex >= 0 ? batchImages[coverIndex].id : null
          setExistingImages((current) => [
            ...current,
            ...batchImages.map((image) => ({
              ...image,
              is_cover: selectedCoverId
                ? image.id === selectedCoverId
                : image.is_cover,
            })),
          ])
          setNewImages((current) => current.filter((file) => !batchFiles.includes(file)))
          if (selectedCoverId) {
            await setCarCover(car.id, selectedCoverId)
            setExistingImages((current) =>
              current.map((image) => ({
                ...image,
                is_cover: image.id === selectedCoverId,
              })),
            )
            setNewCoverFile(null)
          }
        })
        setNewImages([])
        setNewCoverFile(null)
      }
      if (sendForReview && car.status !== 'pending') {
        await submitCar(car.id)
      }
      notify(
        sendForReview ? 'Объявление отправлено на модерацию.' : 'Объявление сохранено.',
        'success',
      )
      navigate('/my-cars')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось сохранить объявление.'))
    } finally {
      setSaving(false)
    }
  }

  const availableModels = lookups.models.filter(
    (model) => !selectedBrandId || String(model.brand) === selectedBrandId,
  )

  if (loading) return <section className="container page-section"><LoadingState label="Загружаем объявление…" /></section>
  if (loadError && isEditing) return <section className="container page-section"><ErrorState message={loadError} onRetry={() => window.location.reload()} /></section>

  return (
    <section className="container page-section car-form-page">
      <Link to="/my-cars" className="back-link"><ArrowLeft size={17} /> Мои объявления</Link>
      <PageTitle eyebrow="Личный кабинет" title={isEditing ? 'Редактировать объявление' : 'Добавить автомобиль'} description="Заполните характеристики и добавьте фотографии автомобиля." />
      {error && <div className="form-alert" role="alert">{error}</div>}
      <form
        className="listing-form"
        onSubmit={(event) =>
          submit(event, event.nativeEvent.submitter?.value === 'publish')
        }
      >
        <section className="form-section">
          <div className="form-section-heading"><span>01</span><div><h2>Основная информация</h2><p>Марка, модель и расположение автомобиля.</p></div></div>
          <div className="form-grid">
            <label className="field-label">Марка<select value={selectedBrandId} onChange={(event) => { setSelectedBrandId(event.target.value); setForm((current) => ({ ...current, model: '' })) }} required><option value="">Выберите марку</option>{lookups.brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label>
            <label className="field-label">Модель<select value={form.model} onChange={update('model')} required><option value="">Выберите модель</option>{availableModels.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}</select></label>
            <label className="field-label">Город<select value={form.city} onChange={update('city')} required><option value="">Выберите город</option>{lookups.cities.map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}</select></label>
            <label className="field-label">Год выпуска<input type="number" min="1886" max="2100" required value={form.year} onChange={update('year')} placeholder="Например, 2020" /></label>
          </div>
        </section>

        <section className="form-section">
          <div className="form-section-heading"><span>02</span><div><h2>Характеристики</h2><p>Помогите покупателю понять, подходит ли ему автомобиль.</p></div></div>
          <div className="form-grid">
            <label className="field-label">Цена, сом<input type="number" min="0" step="1" required value={form.price} onChange={update('price')} placeholder="Например, 1 250 000" /></label>
            <label className="field-label">Пробег, км<input type="number" min="0" required value={form.mileage} onChange={update('mileage')} placeholder="Например, 85 000" /></label>
            <label className="field-label">Тип двигателя<select value={form.engine_type} onChange={update('engine_type')}>{choiceLabels.engine_type.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="field-label">Объём двигателя, л<input type="number" min="0.1" max="99.9" step="0.1" value={form.engine_volume} onChange={update('engine_volume')} placeholder="Например, 2.0" /></label>
            <label className="field-label">Коробка передач<select value={form.transmission} onChange={update('transmission')}>{choiceLabels.transmission.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="field-label">Привод<select value={form.drive_type} onChange={update('drive_type')}>{choiceLabels.drive_type.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="field-label">Тип кузова<select value={form.body_type} onChange={update('body_type')}>{choiceLabels.body_type.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="field-label">Состояние<select value={form.condition} onChange={update('condition')}>{choiceLabels.condition.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          </div>
          <label className="field-label">Описание<textarea rows="5" maxLength="10000" required value={form.description} onChange={update('description')} placeholder="Расскажите о состоянии автомобиля, комплектации и особенностях…" /><small>{form.description.length} / 10 000</small></label>
        </section>

        <section className="form-section">
          <div className="form-section-heading"><span>03</span><div><h2>Фотографии и контакт</h2><p>Добавьте до 20 фото в формате JPG, PNG или WEBP. До 10 МБ на файл.</p></div></div>
          <label className="field-label">Телефон продавца<input type="tel" required value={form.contact_phone} onChange={update('contact_phone')} placeholder="+996700123456" /></label>
          <label className="upload-zone">
            <ImagePlus size={25} />
            <strong>Выберите фотографии автомобиля</strong>
            <span>JPG, JPEG, PNG или WEBP · не более 10 МБ каждое</span>
            <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" multiple onChange={addFiles} />
          </label>
          {(existingImages.length > 0 || previews.length > 0) && (
            <div className="form-photo-grid">
              {existingImages.map((image, index) => (
                <div className="form-photo" key={image.id}>
                  <img src={resolveMediaUrl(image.image)} alt={`Фото объявления ${index + 1}`} />
                  {image.is_cover && <span className="cover-tag"><Star size={12} fill="currentColor" /> Обложка</span>}
                  <div className="photo-controls">
                    <button type="button" onClick={() => moveImage(index, -1)} disabled={index === 0} aria-label="Переместить вверх"><ArrowUp size={15} /></button>
                    <button type="button" onClick={() => moveImage(index, 1)} disabled={index === existingImages.length - 1} aria-label="Переместить вниз"><ArrowDown size={15} /></button>
                    {!image.is_cover && <button type="button" onClick={() => chooseCover(image)} aria-label="Сделать обложкой"><Star size={15} /></button>}
                    <button type="button" onClick={() => removeImage(image)} aria-label="Удалить фотографию"><Trash2 size={15} /></button>
                  </div>
                </div>
              ))}
              {previews.map(({ file, url }, index) => (
                <div className="form-photo" key={`${file.name}-${file.lastModified}`}>
                  <img src={url} alt={file.name} />
                  {newCoverFile === file && <span className="cover-tag"><Star size={12} fill="currentColor" /> Обложка</span>}
                  <div className="photo-controls">
                    <button type="button" onClick={() => removeNewImage(index)} aria-label="Удалить фотографию"><Trash2 size={15} /></button>
                    <button type="button" onClick={() => setNewCoverFile(file)} aria-label="Выбрать обложкой"><Star size={15} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="field-hint">Добавлено: {existingImages.length + newImages.length} / {maxPhotos}. Первая фотография станет обложкой, если вы не выберете её вручную.</p>
        </section>

        <div className="form-actions">
          <Link className="button button--outline" to="/my-cars">Отмена</Link>
          <button className="button button--outline" type="submit" value="draft" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16} /> : null} Сохранить черновик</button>
          <button className="button button--primary" type="submit" value="publish" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16} /> : <Check size={17} />} Сохранить и отправить</button>
        </div>
      </form>
    </section>
  )
}
