import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export default function Reports() {
  const { t } = useTranslation()
  const [year] = useState(2025)
  const { data: transition } = useQuery({
    queryKey: ['reports', 'stock-transition', year],
    queryFn: async () => {
      const { data } = await api.get(`/reports/stock-transition`, { params: { year } })
      return data
    },
  })
  const { data: disposal } = useQuery({
    queryKey: ['reports', 'disposal', year],
    queryFn: async () => {
      const { data } = await api.get(`/reports/disposal`, { params: { year } })
      return data
    },
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{t('reports.title')}</h1>
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-2">{t('reports.stockTransition')}</h2>
        <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-48">
          {JSON.stringify(transition ?? {}, null, 2)}
        </pre>
      </section>
      <section>
        <h2 className="text-lg font-medium mb-2">{t('reports.disposal')}</h2>
        <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-48">
          {JSON.stringify(disposal ?? {}, null, 2)}
        </pre>
      </section>
    </div>
  )
}
