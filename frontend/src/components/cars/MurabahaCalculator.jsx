import { useMemo, useState } from 'react'
import { Landmark } from 'lucide-react'
import { formatPrice } from '../../utils/format.js'

const TERM_STEPS = [3, 6, 12, 18, 24, 36, 48, 60, 72, 84, 96, 120]

// Сроки на выбор: стандартные шаги до максимума салона + сам максимум
function termOptions(max) {
  const options = TERM_STEPS.filter((months) => months < max)
  return [...options, max]
}

// Мурабаха: салон продаёт авто с фиксированной наценкой, без процентов на остаток.
// Наценка = остаток после взноса × % в год × срок в годах; платежи равные.
export function calculateMurabaha(price, { downPercent, months, markupPercent }) {
  const down = price * downPercent / 100
  const financed = price - down
  const markup = financed * markupPercent / 100 * months / 12
  return {
    down,
    financed,
    markup,
    monthly: (financed + markup) / months,
    total: price + markup,
  }
}

export default function MurabahaCalculator({ price, currency, terms }) {
  const amount = Number(price)
  const minDown = terms.min_down_percent
  const termList = useMemo(() => termOptions(terms.max_term_months), [terms.max_term_months])
  const [downPercent, setDownPercent] = useState(Math.max(minDown, 30))
  const [months, setMonths] = useState(termList.includes(12) ? 12 : termList[termList.length - 1])

  if (!Number.isFinite(amount) || amount <= 0) return null

  const down = Math.min(Math.max(downPercent, minDown), 90)
  const result = calculateMurabaha(amount, { downPercent: down, months, markupPercent: terms.markup_percent })
  const money = (value) => formatPrice(Math.round(value), currency)

  return (
    <div className="detail-card murabaha-card">
      <div className="detail-card-heading">
        <h2>Мурабаха</h2>
        <span><Landmark size={16} /> {`Без процентов, наценка ${terms.markup_percent}% в год`}</span>
      </div>
      <div className="murabaha-inputs">
        <label className="field-label">
          <span className="murabaha-label-row">Первый взнос <strong>{`${down}% · ${money(result.down)}`}</strong></span>
          <input
            type="range"
            min={minDown}
            max="90"
            step="1"
            value={down}
            onChange={(e) => setDownPercent(Number(e.target.value))}
            aria-label="Первый взнос, %"
          />
        </label>
        <label className="field-label">
          Срок
          <select value={months} onChange={(e) => setMonths(Number(e.target.value))}>
            {termList.map((value) => <option key={value} value={value}>{`${value} мес.`}</option>)}
          </select>
        </label>
      </div>
      <div className="murabaha-result">
        <div className="murabaha-monthly">
          <span>Ежемесячный платёж</span>
          <strong>{money(result.monthly)}</strong>
        </div>
        <dl className="murabaha-breakdown">
          <div><dt>Сумма рассрочки</dt><dd>{money(result.financed)}</dd></div>
          <div><dt>Наценка салона</dt><dd>{money(result.markup)}</dd></div>
          <div><dt>Итоговая стоимость</dt><dd>{money(result.total)}</dd></div>
        </dl>
      </div>
      {terms.note && <p className="murabaha-note">{terms.note}</p>}
      <p className="field-hint">Расчёт предварительный. Точные условия уточняйте у салона.</p>
    </div>
  )
}
