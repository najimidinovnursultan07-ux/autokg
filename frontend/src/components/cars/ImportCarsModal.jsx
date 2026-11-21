import { useState } from 'react'
import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { downloadImportTemplate, importDashboardCars } from '../../api/cars.js'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

export default function ImportCarsModal({ onClose, onImported }) {
  const { notify } = useToast()
  const [file, setFile] = useState(null)
  const [publish, setPublish] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [errors, setErrors] = useState([])
  const [result, setResult] = useState(null)

  const getTemplate = async () => {
    setDownloading(true)
    try {
      await downloadImportTemplate()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось скачать шаблон.'), 'error')
    } finally {
      setDownloading(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setErrors([])
    try {
      const data = await importDashboardCars(file, publish)
      setResult(data)
      onImported()
    } catch (err) {
      const list = err?.response?.data?.errors
      if (Array.isArray(list)) setErrors(list)
      notify(getErrorMessage(err, 'Не удалось загрузить файл.'), 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <form className="admin-modal admin-modal--wide import-modal" role="dialog" aria-modal="true" aria-labelledby="import-title" onSubmit={submit}>
        <h2 id="import-title"><FileSpreadsheet size={20} /> Загрузка из Excel</h2>

        {result ? (
          <>
            <p className="import-result">
              Загружено объявлений: <strong>{result.created}</strong>.
              {result.published > 0 && <> Опубликовано: <strong>{result.published}</strong>.</>}
              {result.hidden > 0 && <> Сохранено скрытыми: <strong>{result.hidden}</strong> — добавьте фото и опубликуйте.</>}
            </p>
            <div className="admin-modal-actions">
              <button type="button" className="button button--primary" onClick={onClose}>Готово</button>
            </div>
          </>
        ) : (
          <>
            <ol className="import-steps">
              <li>
                Скачайте шаблон — в нём есть пример и выпадающие списки марок, городов и характеристик.
                <button type="button" className="button button--outline" onClick={getTemplate} disabled={downloading}>
                  <Download size={16} /> {downloading ? 'Скачиваем…' : 'Скачать шаблон'}
                </button>
              </li>
              <li>Заполните по одной машине в строке (до 300 за раз). Фото добавляются потом в кабинете.</li>
              <li>
                Загрузите файл .xlsx:
                <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  onChange={(e) => { setFile(e.target.files?.[0] || null); setErrors([]) }} />
              </li>
            </ol>
            <label className="checkbox-label">
              <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} />
              Сразу опубликовать (в пределах лимита тарифа, остальные — скрытыми)
            </label>
            <p className="field-hint">Без галочки все объявления сохранятся скрытыми: добавьте фото и опубликуйте их.</p>

            {errors.length > 0 && (
              <div className="form-alert import-errors" role="alert">
                <strong>Ничего не загружено — исправьте ошибки в файле:</strong>
                <ul>{errors.map((message) => <li key={message}>{message}</li>)}</ul>
              </div>
            )}

            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={onClose}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={!file || uploading}>
                <Upload size={16} /> {uploading ? 'Загружаем…' : 'Загрузить'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  )
}
