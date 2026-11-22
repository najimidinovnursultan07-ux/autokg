import { Fragment } from 'react'
import CarCard from './CarCard.jsx'

// ad — необязательный элемент (рекламный баннер), вставляется после adAfter карточек на всю ширину сетки
export default function CarGrid({ cars, featuredIds = [], ad = null, adAfter = 6 }) {
  const adIndex = Math.min(adAfter, cars.length) - 1
  return (
    <div className="car-grid">
      {cars.map((car, index) => (
        <Fragment key={car.id}>
          <CarCard
            car={car}
            featured={featuredIds.includes(String(car.id))}
          />
          {ad && index === adIndex && <div className="car-grid-ad">{ad}</div>}
        </Fragment>
      ))}
    </div>
  )
}
