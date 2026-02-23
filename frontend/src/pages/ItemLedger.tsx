import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
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
  notes: string | null
}

interface LedgerRow {
  id: string
  item_id: string
  ledger_type: string
  quantity: number
  lot: string | null
  ledger_date: string | null
  process_name: string | null
  status: string
  created_by: string
  created_at: string | null
}

const statusKey: Record<string, string> = {
  PENDING: 'ledgers.statusPending',
  APPROVED: 'ledgers.statusApproved',
  REJECTED: 'ledgers.statusRejected',
}
const typeKey: Record<string, string> = {
  INBOUND: 'ledgers.typeInbound',
  OUTBOUND: 'ledgers.typeOutbound',
  ISSUE: 'ledgers.typeIssue',
  DISPOSAL: 'ledgers.typeDisposal',
}

function formatDate(s: string | null | undefined): string {
  if (!s) return '—'
  try {
    const d = new Date(s)
    return Number.isNaN(d.getTime()) ? s : d.toLocaleDateString('ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return s
  }
}

export default function ItemLedger() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const { data: item, isLoading: itemLoading } = useQuery({
    queryKey: ['item', id],
    queryFn: async () => {
      const { data } = await api.get<Item>(`/items/${id}`)
      return data
    },
    enabled: !!id,
  })
  const { data: ledgers = [], isLoading: ledgersLoading } = useQuery({
    queryKey: ['ledgers', 'item', id],
    queryFn: async () => {
      const { data } = await api.get<LedgerRow[]>('/ledgers', { params: { item_id: id } })
      return data
    },
    enabled: !!id,
  })

  if (!id) return null
  if (itemLoading || !item) return <p>読み込み中...</p>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('itemLedger.title')}</h1>
        <div className="flex gap-2">
          <Link
            to={`/ledgers/new?item_id=${id}`}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            {t('itemLedger.addEntry')}
          </Link>
          <Link to={`/items/${id}`} className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('items.detail')}
          </Link>
          <Link to="/items" className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('items.back')}
          </Link>
        </div>
      </div>

      {/* 上: 品目固定情報 */}
      <section className="bg-white rounded shadow p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 border-b pb-2">{t('itemLedger.itemInfo')}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-3">
          <div>
            <dt className="text-sm text-gray-500">{t('itemLedger.itemId')}</dt>
            <dd className="font-mono font-medium">{item.id}</dd>
          </div>
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
            <dd className="font-semibold text-gray-900">{item.current_qty}</dd>
          </div>
        </div>
      </section>

      {/* 下: 入庫・出庫・払い出し履歴 */}
      <section className="bg-white rounded shadow overflow-hidden">
        <h2 className="text-lg font-semibold text-gray-800 p-4 border-b">{t('itemLedger.history')}</h2>
        {ledgersLoading ? (
          <p className="p-4">読み込み中...</p>
        ) : ledgers.length === 0 ? (
          <p className="p-4 text-gray-500">{t('itemLedger.noHistory')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('itemLedger.date')}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.type')}</th>
                  <th className="px-4 py-2 text-right text-sm font-medium text-gray-700">{t('ledgers.quantity')}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.lot')}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.processName')}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.status')}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.detail')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {ledgers.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm">{formatDate(l.ledger_date ?? l.created_at)}</td>
                    <td className="px-4 py-2">{t(typeKey[l.ledger_type] ?? l.ledger_type)}</td>
                    <td className="px-4 py-2 text-right font-mono">{l.quantity}</td>
                    <td className="px-4 py-2 text-sm">{l.lot ?? '—'}</td>
                    <td className="px-4 py-2 text-sm">{l.process_name ?? '—'}</td>
                    <td className="px-4 py-2">{t(statusKey[l.status] ?? l.status)}</td>
                    <td className="px-4 py-2">
                      <Link to={`/ledgers/${l.id}`} className="text-blue-600 hover:underline text-sm">
                        {t('ledgers.detail')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
