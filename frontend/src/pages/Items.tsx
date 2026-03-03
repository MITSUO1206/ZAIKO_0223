import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface Item {
  id: string
  code: string
  name: string
  model_number?: string | null
  storage_place?: string | null
  last_lot?: string | null
  last_inbound_qty?: number | null
  last_inbound_date?: string | null
  current_qty: number
  safety_stock?: number
  unit_price?: number | null
  notes: string | null
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

export default function Items() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [disposalTarget, setDisposalTarget] = useState<Item | null>(null)
  const [disposalQty, setDisposalQty] = useState('')
  const [disposalReason, setDisposalReason] = useState('')
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['items', q],
    queryFn: async () => {
      const params = q ? { q } : {}
      const { data } = await api.get<Item[]>('/items', { params })
      return data
    },
  })
  const { data: lowStockItems = [] } = useQuery({
    queryKey: ['items', 'low-stock'],
    queryFn: async () => {
      const { data } = await api.get<Item[]>('/items/low-stock')
      return data
    },
  })
  const deleteMutation = useMutation({
    mutationFn: (args: { id: string; reason?: string }) =>
      api.delete(`/items/${args.id}${args.reason ? `?delete_reason=${encodeURIComponent(args.reason)}` : ''}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['items'] }),
  })
  const disposalMutation = useMutation({
    mutationFn: (args: { item_id: string; quantity_disposed: number; reason?: string; unit_price_at_disposal?: number }) =>
      api.post('/disposals', args),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
      qc.invalidateQueries({ queryKey: ['items', 'low-stock'] })
      qc.invalidateQueries({ queryKey: ['ledgers'] })
      setDisposalTarget(null)
      setDisposalQty('')
      setDisposalReason('')
    },
  })

  const openDisposal = (item: Item) => {
    setDisposalTarget(item)
    setDisposalQty('')
    setDisposalReason('')
  }
  const submitDisposal = () => {
    if (!disposalTarget) return
    const qty = parseInt(disposalQty, 10)
    if (!Number.isFinite(qty) || qty < 1 || qty > disposalTarget.current_qty) {
      alert(`廃棄数量は 1 以上かつ在庫数（${disposalTarget.current_qty}）以下で入力してください。`)
      return
    }
    disposalMutation.mutate({
      item_id: disposalTarget.id,
      quantity_disposed: qty,
      reason: disposalReason.trim() || undefined,
      unit_price_at_disposal: disposalTarget.unit_price ?? undefined,
    })
  }

  const handleDelete = (item: Item) => {
    if (!window.confirm(`${item.code} ${item.name} を削除しますか？`)) return
    const reason = window.prompt(t('items.deleteReason') + '（任意）:')
    deleteMutation.mutate({ id: item.id, reason: reason ?? undefined })
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{t('items.title')}</h1>
        <Link
          to="/items/new"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          {t('items.new')}
        </Link>
      </div>
      <div className="mb-4">
        <input
          type="search"
          placeholder={t('items.search')}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 w-64"
        />
      </div>

      {/* 安全在庫を下回っている品目（検索窓の下・行は赤） */}
      {lowStockItems.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">{t('reports.safetyStockAlerts')}</h2>
          <div className="bg-white rounded shadow overflow-x-auto border border-red-200">
            <table className="min-w-full divide-y divide-red-100">
              <thead className="bg-red-50">
                <tr>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.code')}</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.name')}</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.modelNumber')}</th>
                  <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">単価</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.storagePlace')}</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.lastLot')}</th>
                  <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">{t('items.lastInboundQty')}</th>
                  <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.lastInboundDate')}</th>
                  <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">{t('items.currentQty')}</th>
                  <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">{t('items.safetyStock')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-red-100">
                {lowStockItems.map((item) => (
                  <tr key={item.id} className="bg-red-50 hover:bg-red-100">
                    <td className="px-3 py-2">
                      <Link to={`/items/${item.id}`} className="text-blue-600 hover:underline font-medium">{item.code}</Link>
                    </td>
                    <td className="px-3 py-2">{item.name}</td>
                    <td className="px-3 py-2 text-sm">{item.model_number ?? '—'}</td>
                    <td className="px-3 py-2 text-right text-sm">{item.unit_price != null ? Number(item.unit_price).toLocaleString() : '—'}</td>
                    <td className="px-3 py-2 text-sm">{item.storage_place ?? '—'}</td>
                    <td className="px-3 py-2 text-sm">{item.last_lot ?? '—'}</td>
                    <td className="px-3 py-2 text-right text-sm">{item.last_inbound_qty ?? '—'}</td>
                    <td className="px-3 py-2 text-sm">{formatDate(item.last_inbound_date)}</td>
                    <td className="px-3 py-2 text-right font-mono">{item.current_qty}</td>
                    <td className="px-3 py-2 text-right font-mono text-red-700">{item.safety_stock ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isLoading ? (
        <p>読み込み中...</p>
      ) : (
        <div className="bg-white rounded shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.code')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.name')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.modelNumber')}</th>
                <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">単価</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.storagePlace')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.lastLot')}</th>
                <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">{t('items.lastInboundQty')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.lastInboundDate')}</th>
                <th className="px-3 py-2 text-right text-sm font-medium text-gray-700">{t('items.currentQty')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('itemLedger.title')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.detail')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.edit')}</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">廃棄</th>
                <th className="px-3 py-2 text-left text-sm font-medium text-gray-700">{t('items.delete')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{item.code}</td>
                  <td className="px-3 py-2">{item.name}</td>
                  <td className="px-3 py-2 text-sm">{item.model_number ?? '—'}</td>
                  <td className="px-3 py-2 text-right text-sm">{item.unit_price != null ? Number(item.unit_price).toLocaleString() : '—'}</td>
                  <td className="px-3 py-2 text-sm">{item.storage_place ?? '—'}</td>
                  <td className="px-3 py-2 text-sm">{item.last_lot ?? '—'}</td>
                  <td className="px-3 py-2 text-right text-sm">{item.last_inbound_qty ?? '—'}</td>
                  <td className="px-3 py-2 text-sm">{formatDate(item.last_inbound_date)}</td>
                  <td className="px-3 py-2 text-right font-mono">{item.current_qty}</td>
                  <td className="px-3 py-2">
                    <Link to={`/items/${item.id}/ledger`} className="text-blue-600 hover:underline">
                      {t('itemLedger.title')}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/items/${item.id}`} className="text-gray-600 hover:underline">
                      {t('items.detail')}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/items/${item.id}/edit`} className="text-blue-600 hover:underline">
                      {t('items.edit')}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => openDisposal(item)}
                      disabled={item.current_qty < 1}
                      className="text-amber-600 hover:underline text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      廃棄
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => handleDelete(item)}
                      className="text-red-600 hover:underline text-sm"
                    >
                      {t('items.delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {disposalTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setDisposalTarget(null)}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">廃棄登録 — {disposalTarget.code} {disposalTarget.name}</h2>
            <p className="text-sm text-gray-600 mb-2">在庫数: {disposalTarget.current_qty}</p>
            <div className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">廃棄数量 *</label>
              <input
                type="number"
                min={1}
                max={disposalTarget.current_qty}
                value={disposalQty}
                onChange={(e) => setDisposalQty(e.target.value)}
                className="border border-gray-300 rounded px-3 py-2 w-full"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">理由（任意）</label>
              <input
                type="text"
                value={disposalReason}
                onChange={(e) => setDisposalReason(e.target.value)}
                placeholder="例: 破損・期限切れ"
                className="border border-gray-300 rounded px-3 py-2 w-full"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setDisposalTarget(null)} className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50">
                キャンセル
              </button>
              <button type="button" onClick={submitDisposal} disabled={disposalMutation.isPending} className="px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50">
                {disposalMutation.isPending ? '登録中...' : '廃棄登録'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
