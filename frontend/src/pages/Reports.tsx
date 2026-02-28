import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { api } from '../api/client'

const CHAT_PROMPT_TREND = '今の集計・在庫の傾向と注意点を教えて'

export default function Reports() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)

  const { data: dashboard } = useQuery({
    queryKey: ['reports', 'dashboard'],
    queryFn: async () => {
      const { data } = await api.get('/reports/dashboard')
      return data
    },
  })

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

  const { data: alerts } = useQuery({
    queryKey: ['reports', 'safety-stock-alerts'],
    queryFn: async () => {
      const { data } = await api.get('/reports/safety-stock-alerts')
      return data
    },
  })

  // 在庫推移: 全品目を月別に合計したデータ
  const transitionChartData = useMemo(() => {
    if (!transition?.data || typeof transition.data !== 'object') return []
    const byPeriod: Record<string, number> = {}
    for (const itemId of Object.keys(transition.data)) {
      const points = (transition.data as Record<string, { period: string; delta: number }[]>)[itemId] || []
      for (const p of points) {
        byPeriod[p.period] = (byPeriod[p.period] || 0) + (p.delta ?? 0)
      }
    }
    return Object.entries(byPeriod)
      .map(([period, total]) => ({ period, total: Number(total) }))
      .sort((a, b) => a.period.localeCompare(b.period))
  }, [transition])

  // 廃棄: 品目別に数量を集計（品目名で表示）
  const disposalByItem = useMemo(() => {
    if (!disposal?.items?.length) return []
    const byItem: Record<string, { item_code: string; item_name: string; quantity: number; amount: number }> = {}
    for (const row of disposal.items) {
      const id = row.item_id
      if (!byItem[id]) {
        byItem[id] = {
          item_code: row.item_code ?? '',
          item_name: row.item_name ?? row.item_id,
          quantity: 0,
          amount: 0,
        }
      }
      byItem[id].quantity += row.quantity ?? 0
      byItem[id].amount += row.amount ?? 0
    }
    return Object.values(byItem).sort((a, b) => b.quantity - a.quantity).slice(0, 10)
  }, [disposal])

  const kpis = [
    { label: t('reports.kpi.totalItems'), value: dashboard?.total_items ?? '-' },
    { label: t('reports.kpi.totalStockQty'), value: dashboard?.total_stock_quantity ?? '-' },
    { label: t('reports.kpi.totalStockValue'), value: dashboard?.total_stock_value != null ? `¥${Number(dashboard.total_stock_value).toLocaleString()}` : '-' },
    { label: t('reports.kpi.pendingCount'), value: dashboard?.pending_ledgers_count ?? '-' },
    { label: t('reports.kpi.thisMonthLedgers'), value: dashboard?.this_month_ledgers_count ?? '-' },
    { label: t('reports.kpi.thisMonthDisposal'), value: dashboard?.this_month_disposal_quantity ?? '-' },
    { label: t('reports.kpi.thisMonthDisposalAmount'), value: dashboard?.this_month_disposal_amount != null ? `¥${Number(dashboard.this_month_disposal_amount).toLocaleString()}` : '-' },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t('reports.title')}</h1>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            onClick={() => navigate(`/chat?prompt=${encodeURIComponent(CHAT_PROMPT_TREND)}`)}
            className="text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {t('reports.askTrendInChat')}
          </button>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">{t('reports.year')}</label>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          >
            {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          </div>
        </div>
      </div>

      {/* KPI カード */}
      <section>
        <h2 className="text-lg font-medium mb-3">{t('reports.dashboard')}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {kpis.map((k) => (
            <div key={k.label} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="text-xs text-gray-500 truncate">{k.label}</div>
              <div className="text-lg font-semibold mt-1">{k.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 安全在庫アラート */}
      <section>
        <h2 className="text-lg font-medium mb-3">{t('reports.safetyStockAlerts')}</h2>
        {alerts?.items?.length ? (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left py-2 px-3">{t('items.code')}</th>
                  <th className="text-left py-2 px-3">{t('items.name')}</th>
                  <th className="text-right py-2 px-3">{t('items.currentQty')}</th>
                  <th className="text-right py-2 px-3">{t('items.safetyStock')}</th>
                  <th className="text-left py-2 px-3">{t('items.unit')}</th>
                </tr>
              </thead>
              <tbody>
                {alerts.items.map((a: { id: string; code: string; name: string; current_qty: number; safety_stock: number; unit?: string }) => (
                  <tr key={a.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3">
                      <Link to={`/items/${a.id}`} className="text-blue-600 hover:underline">{a.code}</Link>
                    </td>
                    <td className="py-2 px-3">{a.name}</td>
                    <td className="text-right py-2 px-3">{a.current_qty}</td>
                    <td className="text-right py-2 px-3">{a.safety_stock}</td>
                    <td className="py-2 px-3">{a.unit ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">{t('reports.noSafetyAlerts')}</p>
        )}
      </section>

      {/* 在庫推移グラフ */}
      <section>
        <h2 className="text-lg font-medium mb-3">{t('reports.stockTransition')}（{year}）</h2>
        {transitionChartData.length > 0 ? (
          <div className="h-64 bg-white border border-gray-200 rounded-lg p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={transitionChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value: number) => [value, t('reports.delta')]} />
                <Legend />
                <Line type="monotone" dataKey="total" name={t('reports.totalDelta')} stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">{t('reports.noTransitionData')}</p>
        )}
      </section>

      {/* 廃棄 品目別 棒グラフ */}
      <section>
        <h2 className="text-lg font-medium mb-3">{t('reports.disposal')}（{year}）{t('reports.byItem')}</h2>
        {disposalByItem.length > 0 ? (
          <div className="h-80 bg-white border border-gray-200 rounded-lg p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={disposalByItem} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="item_name" width={75} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="quantity" name={t('reports.disposalQty')} fill="#dc2626" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">{t('reports.noDisposalData')}</p>
        )}
      </section>
    </div>
  )
}
