import CarCard from './CarCard.jsx'

export default function CarGrid({ cars, featuredIds = [] }) {
  return (
    <div className="car-grid">
      {cars.map((car) => (
        <CarCard
          key={car.id}
          car={car}
          featured={featuredIds.includes(String(car.id))}
        />
      ))}
    </div>
  )
}
