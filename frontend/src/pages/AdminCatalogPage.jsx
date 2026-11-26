import { useCallback, useEffect, useMemo, useState } from 'react'
import { Check, Pencil, Plus, Search, ToggleLeft, ToggleRight, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import {
  createAdminCatalogItem,
  deleteAdminCatalogItem,
  getAdminCatalog,
  updateAdminCatalogItem,
} from '../api/admin.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { VEHICLE_LABELS, VEHICLE_TYPES } from '../utils/vehicles.js'

const PAGE_SIZE = 10
const catalogTabs = [
  { id: 'brands', label: 'Марки' },
  { id: 'models', label: 'Модели' },
  { id: 'cities', label: 'Города' },
]
const catalogNouns = { brands: 'марку', models: 'модель', cities: 'город' }

function initialForm(kind, brands = []) {
  return {
    name: '',
    slug: '',
    is_active: true,
    brand: kind === 'models' ? String(brands[0]?.id || '') : '',
    vehicle_type: 'car',
  }
}

export default function AdminCatalogPage() {
  const { notify } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [kind, setKind] = useState('brands')
  const search = searchParams.get('search') || ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const [searchInput, setSearchInput] = useState(search)
  const [items, setItems] = useState([])
  const [brands, setBrands] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [workingId, setWorkingId] = useState(null)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(() => initialForm('brands'))

  const brandNames = useMemo(
    () => new Map(brands.map((brand) => [brand.id, brand.name])),
    [brands],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [response, brandResponse] = await Promise.all([
        getAdminCatalog(kind, { search: search || undefined, page, page_size: PAGE_SIZE }),
        kind === 'models'
          ? getAdminCatalog('brands', { page_size: 100 })
          : Promise.resolve(null),
      ])
      setItems(response.results || [])
      setCount(response.count || 0)
      if (brandResponse) setBrands(brandResponse.results || [])
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить справочник.'))
    } finally {
      setLoading(false)
    }
  }, [kind, page, search])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setSearchInput(search)
  }, [search])

  useEffect(() => {
    setEditingId(null)
    setForm(initialForm(kind, brands))
  }, [kind, brands])

  const chooseKind = (nextKind) => {
    if (nextKind === kind) return
    setKind(nextKind)
    setSearchParams({})
    setEditingId(null)
  }

  const applySearch = (event) => {
    event.preventDefault()
    const next = new URLSearchParams()
    const value = searchInput.trim()
    if (value) next.set('search', value)
    setSearchParams(next)
  }

  const changePage = (nextPage) => {
    const next = new URLSearchParams(searchParams)
    if (nextPage > 1) next.set('page', String(nextPage))
    else next.delete('page')
    setSearchParams(next)
  }

  const editItem = (item) => {
    setEditingId(item.id)
    setForm({
      name: item.name,
      slug: item.slug,
      is_active: item.is_active,
      brand: kind === 'models' ? String(item.brand) : '',
      vehicle_type: item.vehicle_type || 'car',
    })
  }

  const resetForm = () => {
    setEditingId(null)
    setForm(initialForm(kind, brands))
  }

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim(),
      is_active: form.is_active,
    }
    if (kind === 'models') {
      payload.brand = Number(form.brand)
      payload.vehicle_type = form.vehicle_type
    }
    try {
      if (editingId) {
        await updateAdminCatalogItem(kind, editingId, payload)
        notify('Изменения сохранены.', 'success')
      } else {
        await createAdminCatalogItem(kind, payload)
        notify('Элемент справочника добавлен.', 'success')
      }
      resetForm()
      await load()
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось сохранить элемент справочника.'))
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (item) => {
    setWorkingId(item.id)
    try {
      await updateAdminCatalogItem(kind, item.id, { is_active: !item.is_active })
      notify(item.is_active ? 'Элемент деактивирован.' : 'Элемент активирован.', 'success')
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось изменить состояние элемента.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const remove = async (item) => {
    if (!window.confirm(`Удалить «${item.name}»? Используемые элементы нельзя удалить — их можно деактивировать.`)) return
    setWorkingId(item.id)
    try {
      await deleteAdminCatalogItem(kind, item.id)
      notify('Элемент удалён.', 'success')
      if (editingId === item.id) resetForm()
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось удалить элемент справочника.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Справочники" description="Управляйте марками, моделями автомобилей и городами." />
      <nav className="admin-tabs" aria-label="Тип справочника">
        {catalogTabs.map((tab) => (
          <button type="button" className={`admin-tab ${kind === tab.id ? 'admin-tab--active' : ''}`} onClick={() => chooseKind(tab.id)} key={tab.id}>
            {tab.label}
          </button>
        ))}
      </nav>
      <div className="admin-catalog-layout">
        <form className="admin-catalog-form form-stack" onSubmit={submit}>
          <div className="admin-form-heading">
            <h2>{editingId ? 'Редактировать' : 'Добавить'} {catalogNouns[kind]}</h2>
            {editingId && <button type="button" className="icon-action" aria-label="Отменить редактирование" onClick={resetForm}><X size={17} /></button>}
          </div>
          {error && <div className="form-alert" role="alert">{error}</div>}
          <label className="field-label">Название<input required maxLength={100} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">URL-идентификатор<input required maxLength={120} value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} /></label>
          {kind === 'models' && (
            <label className="field-label">Марка
              <select required value={form.brand} onChange={(event) => setForm({ ...form, brand: event.target.value })}>
                <option value="">Выберите марку</option>
                {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}{brand.is_active ? '' : ' (неактивна)'}</option>)}
              </select>
            </label>
          )}
          {kind === 'models' && (
            <label className="field-label">Вид транспорта
              <select value={form.vehicle_type} onChange={(event) => setForm({ ...form, vehicle_type: event.target.value })}>
                {VEHICLE_TYPES.map(({ value, single }) => <option key={value} value={value}>{single}</option>)}
              </select>
            </label>
          )}
          <label className="admin-checkbox-label"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /> Активен и доступен в каталоге</label>
          <button type="submit" className="button button--primary" disabled={saving || (kind === 'models' && !form.brand)}>
            {editingId ? <Check size={16} /> : <Plus size={16} />}
            {saving ? 'Сохраняем…' : editingId ? 'Сохранить' : 'Добавить'}
          </button>
        </form>

        <div className="admin-catalog-results">
          <form className="admin-search-form" onSubmit={applySearch}>
            <Search size={18} />
            <input type="search" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Поиск по названию" aria-label="Поиск по справочнику" />
            <button type="submit" className="button button--primary">Найти</button>
          </form>
          {loading ? <LoadingState label="Загружаем справочник…" /> : error && !items.length ? (
            <ErrorState message={error} onRetry={load} />
          ) : items.length ? (
            <>
              <div className="admin-catalog-list">
                {items.map((item) => (
                  <article className="admin-catalog-row" key={item.id}>
                    <span className="admin-catalog-row-copy">
                      <strong>{item.name}</strong>
                      <small>{kind === 'models' ? `${brandNames.get(item.brand) || 'Марка'} · ${VEHICLE_LABELS[item.vehicle_type] || 'Автомобиль'} · ` : ''}{item.slug}</small>
                    </span>
                    <span className={`admin-status ${item.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{item.is_active ? 'Активен' : 'Неактивен'}</span>
                    <div className="admin-catalog-actions">
                      <button type="button" className="icon-action" aria-label="Редактировать" onClick={() => editItem(item)}><Pencil size={16} /></button>
                      <button type="button" className="icon-action" disabled={workingId === item.id} aria-label={item.is_active ? 'Деактивировать' : 'Активировать'} onClick={() => toggleActive(item)}>{item.is_active ? <ToggleRight size={17} /> : <ToggleLeft size={17} />}</button>
                      <button type="button" className="icon-action icon-action--danger" disabled={workingId === item.id} aria-label="Удалить" onClick={() => remove(item)}><Trash2 size={16} /></button>
                    </div>
                  </article>
                ))}
              </div>
              {pageCount > 1 && (
                <div className="admin-pagination">
                  <span>{count} элементов · страница {page} из {pageCount}</span>
                  <div>
                    <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => changePage(page - 1)}>Назад</button>
                    <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => changePage(page + 1)}>Далее</button>
                  </div>
                </div>
              )}
            </>
          ) : <div className="admin-empty">Элементы не найдены.</div>}
        </div>
      </div>
    </section>
  )
}
