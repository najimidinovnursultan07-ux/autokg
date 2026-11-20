import { useMemo, useState } from 'react'
import { MapPin, X } from 'lucide-react'
import TwoGisMap from './TwoGisMap.jsx'
import { hasLocation, parseLocation, toLatLng, twoGisPointUrl } from '../../utils/twoGis.js'

const round = (value) => Number(value).toFixed(6)

/** Выбор точки салона: клик по карте или вставка ссылки/координат из 2ГИС. */
export default function LocationPicker({ latitude, longitude, onChange }) {
  const [pasted, setPasted] = useState('')
  const [pasteError, setPasteError] = useState('')
  const selected = hasLocation({ latitude, longitude })
  const position = useMemo(
    () => (selected ? toLatLng({ latitude, longitude }) : null),
    [selected, latitude, longitude],
  )
  const markers = useMemo(() => (position ? [{ id: 'point', position }] : []), [position])

  const applyPasted = () => {
    const parsed = parseLocation(pasted)
    if (!parsed) {
      setPasteError('Не получилось найти координаты. Вставьте ссылку из 2ГИС или координаты вида 42.8746, 74.5698.')
      return
    }
    setPasteError('')
    setPasted('')
    onChange(round(parsed[0]), round(parsed[1]))
  }

  return (
    <div className="location-picker">
      <div className="location-picker-head">
        <span className="field-label-text"><MapPin size={15} /> Точка на карте</span>
        {selected ? (
          <span className="location-picker-value">
            <a href={twoGisPointUrl(latitude, longitude)} target="_blank" rel="noopener noreferrer">{Number(latitude).toFixed(5)}, {Number(longitude).toFixed(5)}</a>
            <button type="button" className="location-picker-clear" onClick={() => onChange('', '')} aria-label="Убрать точку"><X size={14} /> Убрать</button>
          </span>
        ) : <small>Нажмите на карту там, где находится салон</small>}
      </div>
      <TwoGisMap
        markers={markers}
        center={position || undefined}
        height={280}
        onMapClick={(lat, lng) => onChange(round(lat), round(lng))}
      />
      <div className="location-picker-paste">
        <input
          value={pasted}
          onChange={(e) => setPasted(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); applyPasted() } }}
          placeholder="или вставьте ссылку из 2ГИС / координаты"
          aria-label="Ссылка из 2ГИС или координаты"
        />
        <button type="button" className="button button--outline" onClick={applyPasted} disabled={!pasted.trim()}>Применить</button>
      </div>
      {pasteError && <small className="location-picker-error">{pasteError}</small>}
    </div>
  )
}
