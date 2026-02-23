import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Alerts() {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ['alerts', 'check'],
    queryFn: async () => {
      const { data: res } = await api.get<{ items_below_safety_stock: Array<{ item_id: string; code: string; name: string; current_qty: number; safety_stock: number }> }>('/notifications/alerts/check')
      return res
    },
  })
  const items = data?.items_below_safety_stock ?? []

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{t('alerts.title')}</h1>
      <p className="mb-4">{t('alerts.check')}</p>
      {isLoading ? (
        <p>読み込み中...</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500">安全在庫を下回っている品目はありません。</p>
      ) : (
        <ul className="space-y-2">
          {items.map((i) => (
            <li key={i.item_id} className="flex gap-4 items-center">
              <Link to={`/items/${i.item_id}`} className="text-blue-600 hover:underline">{i.code} {i.name}</Link>
              <span>現在庫: {i.current_qty} / 安全在庫: {i.safety_stock}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
