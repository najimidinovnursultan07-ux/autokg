import { useEffect, useState } from 'react'
import { ImagePlus, Save, Trash2, UserRound } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { updateProfile } from '../api/auth.js'
import { resolveMediaUrl } from '../api/client.js'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { PageTitle } from '../components/common/States.jsx'

const MAX_PROFILE_PHOTO_BYTES = 10 * 1024 * 1024
const PROFILE_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const { notify } = useToast()
  const [form, setForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone: user?.phone || '',
  })
  const [photoFile, setPhotoFile] = useState(null)
  const [photoPreview, setPhotoPreview] = useState('')
  const [removePhoto, setRemovePhoto] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase()
  const currentPhoto = user?.profile_photo ? resolveMediaUrl(user.profile_photo) : ''
  const displayedPhoto = photoPreview || (!removePhoto ? currentPhoto : '')

  useEffect(() => () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview)
  }, [photoPreview])

  const selectPhoto = (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (!PROFILE_PHOTO_TYPES.includes(file.type)) {
      setError('Выберите изображение в формате JPG, PNG или WEBP.')
      return
    }
    if (file.size > MAX_PROFILE_PHOTO_BYTES) {
      setError('Размер фотографии не должен превышать 10 МБ.')
      return
    }
    setError('')
    setPhotoFile(file)
    setPhotoPreview(URL.createObjectURL(file))
    setRemovePhoto(false)
  }

  const clearPhoto = () => {
    setPhotoFile(null)
    setPhotoPreview('')
    setRemovePhoto(true)
  }

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      let payload = form
      if (photoFile) {
        payload = new FormData()
        Object.entries(form).forEach(([key, value]) => payload.append(key, value))
        payload.append('profile_photo', photoFile)
      } else if (removePhoto) {
        payload = { ...form, profile_photo: null }
      }
      const updated = await updateProfile(payload)
      setUser(updated)
      setPhotoFile(null)
      setPhotoPreview('')
      setRemovePhoto(false)
      notify('Профиль обновлён.', 'success')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось сохранить профиль.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="account-page">
      <PageTitle eyebrow="Личный кабинет" title="Мой профиль" description="Обновите контактные данные вашего аккаунта." />
      <div className="profile-layout">
        <div className="profile-summary">
          <div className="profile-avatar">
            {displayedPhoto ? <img src={displayedPhoto} alt="Фото профиля" /> : initials || <UserRound size={28} />}
          </div>
          <strong>{user?.first_name} {user?.last_name}</strong>
          <span>{user?.email}</span>
          <span className="profile-role">{user?.role === 'admin' ? 'Администратор' : 'Пользователь AutoKG'}</span>
          <label className="button button--secondary profile-photo-button" htmlFor="profile-photo">
            <ImagePlus size={16} /> Изменить фото
          </label>
          <input id="profile-photo" className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={selectPhoto} />
          {(currentPhoto || photoFile) && (
            <button type="button" className="text-link profile-photo-remove" onClick={clearPhoto} disabled={loading}>
              <Trash2 size={15} /> Удалить фото
            </button>
          )}
        </div>
        <form className="profile-form form-stack" onSubmit={submit}>
          {error && <div className="form-alert" role="alert">{error}</div>}
          <label className="field-label">Имя<input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label>
          <label className="field-label">Фамилия<input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label>
          <label className="field-label">Телефон<input required type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <label className="field-label">Электронная почта<input value={user?.email || ''} disabled /><small>Изменение email пока недоступно.</small></label>
          <button className="button button--primary" type="submit" disabled={loading}><Save size={17} /> {loading ? 'Сохраняем…' : 'Сохранить изменения'}</button>
        </form>
      </div>
    </section>
  )
}
