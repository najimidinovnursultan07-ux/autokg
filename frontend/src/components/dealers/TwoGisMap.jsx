import { useEffect, useRef, useState } from 'react'
import { DEFAULT_CENTER, loadTwoGis } from '../../utils/twoGis.js'

/**
 * Карта 2ГИС.
 * markers: [{ id, position: [lat, lng], popup?: HTMLElement | string }]
 * onMapClick: (lat, lng) => void — выбор точки кликом (форма профиля салона)
 */
export default function TwoGisMap({ markers = [], center, zoom = 13, onMapClick, className = '', height = 320 }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layerRef = useRef(null)
  const clickRef = useRef(onMapClick)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    clickRef.current = onMapClick
  }, [onMapClick])

  // Создание карты — один раз
  useEffect(() => {
    let cancelled = false
    loadTwoGis()
      .then((DG) => {
        if (cancelled || !containerRef.current) return
        const map = DG.map(containerRef.current, {
          center: center || DEFAULT_CENTER,
          zoom,
          fullscreenControl: false,
          scrollWheelZoom: false,
        })
        map.on('click', (event) => clickRef.current?.(event.latlng.lat, event.latlng.lng))
        layerRef.current = DG.featureGroup().addTo(map)
        mapRef.current = map
        setStatus('ready')
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => {
      cancelled = true
      mapRef.current?.remove()
      mapRef.current = null
      layerRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Маркеры и границы
  useEffect(() => {
    const DG = window.DG
    const map = mapRef.current
    const layer = layerRef.current
    if (status !== 'ready' || !DG || !map || !layer) return
    layer.clearLayers()
    markers.forEach((item) => {
      const marker = DG.marker(item.position).addTo(layer)
      if (item.popup) marker.bindPopup(item.popup)
    })
    if (markers.length > 1) {
      map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 15 })
    } else if (markers.length === 1) {
      map.setView(markers[0].position, Math.max(map.getZoom(), 15))
    } else if (center) {
      map.setView(center, zoom)
    }
  }, [markers, status, center, zoom])

  return (
    <div className={`twogis-map ${className}`} style={{ height }}>
      <div ref={containerRef} className="twogis-map-canvas" />
      {status === 'loading' && <div className="twogis-map-overlay">Загружаем карту 2ГИС…</div>}
      {status === 'error' && <div className="twogis-map-overlay">Карта не загрузилась. Проверьте интернет и обновите страницу.</div>}
    </div>
  )
}
