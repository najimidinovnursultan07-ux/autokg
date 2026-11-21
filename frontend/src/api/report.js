import { api } from './client.js'
import { downloadFile } from './download.js'

// Отчёт салона за месяц: month = 'ГГГГ-ММ' (по умолчанию текущий)
export async function getDealerReport(month) {
  const { data } = await api.get('/dashboard/report/', { params: month ? { month } : {} })
  return data
}

// PDF — не больше 2 раз в месяц (лимит проверяет сервер)
export function downloadDealerReportPdf(month) {
  return downloadFile(`/dashboard/report/pdf/?month=${encodeURIComponent(month)}`, `autobuy-otchet-${month}.pdf`)
}
