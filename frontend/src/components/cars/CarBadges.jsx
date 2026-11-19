export default function CarBadges({ car, size = 'md' }) {
  if (!car) return null
  const { is_top, is_highlighted, is_urgent } = car
  if (!is_top && !is_highlighted && !is_urgent) return null

  return (
    <div className={`car-badges car-badges--${size}`}>
      {is_top && <span className="car-badge car-badge--top">ТОП</span>}
      {is_urgent && <span className="car-badge car-badge--urgent">СРОЧНО</span>}
      {is_highlighted && <span className="car-badge car-badge--highlight">Выделено</span>}
    </div>
  )
}
