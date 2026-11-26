import { Bike, CarFront, Motorbike, Scooter, Truck } from 'lucide-react'

// Виды транспорта (как VehicleType в backend/apps/cars/models.py)
export const VEHICLE_TYPES = [
  { value: 'car', label: 'Авто', single: 'Автомобиль', icon: CarFront },
  { value: 'moto', label: 'Мото и мопеды', single: 'Мото / мопед', icon: Motorbike },
  { value: 'muravey', label: 'Муравьи', single: 'Муравей', icon: Truck },
  { value: 'bicycle', label: 'Велосипеды', single: 'Велосипед', icon: Bike },
  { value: 'scooter', label: 'Самокаты', single: 'Самокат', icon: Scooter },
]

export const VEHICLE_LABELS = Object.fromEntries(VEHICLE_TYPES.map((item) => [item.value, item.single]))

// Какие характеристики есть у вида транспорта
const SPECS = {
  car: { engine: true, engineRequired: true, electricOnly: false, engineVolume: true, transmission: true, transmissionRequired: true, drive: true, body: true, mileage: true },
  moto: { engine: true, engineRequired: true, electricOnly: false, engineVolume: true, transmission: true, transmissionRequired: false, drive: false, body: false, mileage: true },
  muravey: { engine: true, engineRequired: true, electricOnly: false, engineVolume: true, transmission: true, transmissionRequired: false, drive: false, body: false, mileage: true },
  bicycle: { engine: true, engineRequired: false, electricOnly: true, engineVolume: false, transmission: false, transmissionRequired: false, drive: false, body: false, mileage: false },
  scooter: { engine: true, engineRequired: false, electricOnly: true, engineVolume: false, transmission: false, transmissionRequired: false, drive: false, body: false, mileage: true },
}

export function vehicleSpecs(type) {
  return SPECS[type] || SPECS.car
}
