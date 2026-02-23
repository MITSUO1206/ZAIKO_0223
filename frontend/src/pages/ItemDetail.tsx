import { useParams, Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface Item {
  id: string
  code: string
  name: string
  model_number?: string | null
  category?: string | null
  unit?: string | null
  unit_price?: number | null
  safety_stock?: number
  storage_place?: string | null
  current_qty: number
  last_lot?: string | null
  last_inbound_qty?: number | null
  last_inbound_date?: string | null
  notes: string | null
}

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: item, isLoading } = useQuery({
    queryKey: ['item', id],
    queryFn: async () => {
      const { data } = await api.get<Item>(`/items/${id}`)
      return data
    },
    enabled: !!id,
  })
  const deleteMutation = useMutation({
    mutationFn: (reason?: string) => api.delete(`/items/${id}${reason ? `?delete_reason=${encodeURIComponent(reason)}` : ''}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
      navigate('/items')
    },
  })

  if (!id) return null
  if (isLoading || !item) return <p>読み込み中...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{t('items.detail')}</h1>
        <div className="flex gap-2">
          <Link to={`/items/${id}/ledger`} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {t('itemLedger.title')}
          </Link>
          <Link to={`/items/${id}/edit`} className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('items.edit')}
          </Link>
          <button
            type="button"
            onClick={() => {
              const reason = window.prompt('論理削除しますか？ 削除理由（任意）:')
              if (reason !== null) deleteMutation.mutate(reason || undefined)
            }}
            className="bg-red-100 text-red-700 px-4 py-2 rounded hover:bg-red-200"
          >
            {t('items.delete')}
          </button>
          <Link to="/items" className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('items.back')}
          </Link>
        </div>
      </div>
      <div className="bg-white rounded shadow p-6 max-w-md">
        <dl className="space-y-2">
          <div>
            <dt className="text-sm text-gray-500">{t('items.code')}</dt>
            <dd className="font-medium">{item.code}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">{t('items.name')}</dt>
            <dd className="font-medium">{item.name}</dd>
          </div>
          {(item.model_number != null && item.model_number !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.modelNumber')}</dt>
              <dd>{item.model_number}</dd>
            </div>
          )}
          {(item.category != null && item.category !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.category')}</dt>
              <dd>{item.category}</dd>
            </div>
          )}
          {(item.unit != null && item.unit !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.unit')}</dt>
              <dd>{item.unit}</dd>
            </div>
          )}
          {(item.unit_price != null && item.unit_price !== 0) && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.unitPrice')}</dt>
              <dd>{item.unit_price}</dd>
            </div>
          )}
          <div>
            <dt className="text-sm text-gray-500">{t('items.safetyStock')}</dt>
            <dd>{item.safety_stock ?? 0}</dd>
          </div>
          {(item.storage_place != null && item.storage_place !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.storagePlace')}</dt>
              <dd>{item.storage_place}</dd>
            </div>
          )}
          <div>
            <dt className="text-sm text-gray-500">{t('items.currentQty')}</dt>
            <dd className="font-medium">{item.current_qty}</dd>
          </div>
          {(item.last_lot != null && item.last_lot !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.lastLot')}</dt>
              <dd>{item.last_lot}</dd>
            </div>
          )}
          {(item.last_inbound_qty != null) && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.lastInboundQty')}</dt>
              <dd>{item.last_inbound_qty}</dd>
            </div>
          )}
          {(item.last_inbound_date != null && item.last_inbound_date !== '') && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.lastInboundDate')}</dt>
              <dd>{new Date(item.last_inbound_date).toLocaleDateString('ja-JP')}</dd>
            </div>
          )}
          {item.notes && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.notes')}</dt>
              <dd>{item.notes}</dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  )
}
