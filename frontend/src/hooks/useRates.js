import { useEffect, useState } from 'react'
import { getRates } from '../api/rates.js'

export default function useRates() {
  const [rates, setRates] = useState(null)
  useEffect(() => {
    let alive = true
    getRates().then((data) => { if (alive) setRates(data) })
    return () => { alive = false }
  }, [])
  return rates
}
