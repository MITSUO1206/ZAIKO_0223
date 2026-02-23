import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface Ledger {
  id: string
  item_id: string
  ledger_type: string
  quantity: number
  status: string
  created_by: string
  notes: string | null
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

export default function Ledgers() {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const { data: ledgers = [], isLoading } = useQuery({
    queryKey: ['ledgers', q],
    queryFn: async () => {
      const params = q ? { q } : {}
      const { data } = await api.get<Ledger[]>('/ledgers', { params })
      return data
    },
  })

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{t('ledgers.title')}</h1>
        <Link to="/ledgers/new" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {t('ledgers.new')}
        </Link>
      </div>
      <div className="mb-4">
        <input
          type="search"
          placeholder={t('ledgers.search')}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 w-64"
        />
      </div>
      {isLoading ? (
        <p>読み込み中...</p>
      ) : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">ID</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.item')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.type')}</th>
                <th className="px-4 py-2 text-right text-sm font-medium text-gray-700">{t('ledgers.quantity')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.status')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.detail')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {ledgers.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-sm">{l.id}</td>
                  <td className="px-4 py-2">{l.item_id}</td>
                  <td className="px-4 py-2">{t(typeKey[l.ledger_type] ?? l.ledger_type)}</td>
                  <td className="px-4 py-2 text-right">{l.quantity}</td>
                  <td className="px-4 py-2">{t(statusKey[l.status] ?? l.status)}</td>
                  <td className="px-4 py-2">
                    <Link to={`/ledgers/${l.id}`} className="text-blue-600 hover:underline">
                      {t('ledgers.detail')}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
