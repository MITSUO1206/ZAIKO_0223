import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { Link } from 'react-router-dom'

interface Ledger {
  id: string
  item_id: string
  ledger_type: string
  quantity: number
  status: string
  created_by: string
  notes: string | null
}

const typeKey: Record<string, string> = {
  INBOUND: 'ledgers.typeInbound',
  OUTBOUND: 'ledgers.typeOutbound',
  ISSUE: 'ledgers.typeIssue',
  DISPOSAL: 'ledgers.typeDisposal',
}

export default function Approval() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [comment, setComment] = useState('')
  const [actingId, setActingId] = useState<string | null>(null)
  const { data: pending = [], isLoading } = useQuery({
    queryKey: ['ledgers', 'approval', 'pending'],
    queryFn: async () => {
      const { data } = await api.get<Ledger[]>('/ledgers/approval/pending')
      return data
    },
  })
  const approveMutation = useMutation({
    mutationFn: ({ id, comment: c }: { id: string; comment?: string }) =>
      api.post(`/ledgers/${id}/approve`, { comment: c || null }),
    onSuccess: (_, v) => {
      setActingId(null)
      qc.invalidateQueries({ queryKey: ['ledgers'] })
      qc.invalidateQueries({ queryKey: ['ledgers', 'approval', 'pending'] })
    },
  })
  const rejectMutation = useMutation({
    mutationFn: ({ id, comment: c }: { id: string; comment?: string }) =>
      api.post(`/ledgers/${id}/reject`, { comment: c || null }),
    onSuccess: () => {
      setActingId(null)
      qc.invalidateQueries({ queryKey: ['ledgers'] })
      qc.invalidateQueries({ queryKey: ['ledgers', 'approval', 'pending'] })
    },
  })

  const handleApprove = (id: string) => {
    setActingId(id)
    approveMutation.mutate(
      { id, comment: comment || undefined },
      {
        onError: (err: { response?: { status: number; data?: { detail?: string } } }) => {
          if (err.response?.status === 409) {
            alert(t('approval.insufficientStock'))
          } else {
            alert(err.response?.data?.detail ?? t('common.error'))
          }
          setActingId(null)
        },
      }
    )
  }
  const handleReject = (id: string) => {
    setActingId(id)
    rejectMutation.mutate({ id, comment: comment || undefined })
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{t('approval.title')}</h1>
      <p className="mb-4 text-gray-600">{t('approval.pendingList')}</p>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">{t('approval.comment')}</label>
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 w-64"
          placeholder="任意"
        />
      </div>
      {isLoading ? (
        <p>読み込み中...</p>
      ) : pending.length === 0 ? (
        <p className="text-gray-500">{t('approval.noPending')}</p>
      ) : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">ID</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.item')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.type')}</th>
                <th className="px-4 py-2 text-right text-sm font-medium text-gray-700">{t('ledgers.quantity')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('ledgers.createdBy')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {pending.map((l) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-sm">
                    <Link to={`/ledgers/${l.id}`} className="text-blue-600 hover:underline">{l.id}</Link>
                  </td>
                  <td className="px-4 py-2">{l.item_id}</td>
                  <td className="px-4 py-2">{t(typeKey[l.ledger_type] ?? l.ledger_type)}</td>
                  <td className="px-4 py-2 text-right">{l.quantity}</td>
                  <td className="px-4 py-2">{l.created_by}</td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={actingId !== null}
                        onClick={() => handleApprove(l.id)}
                        className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 disabled:opacity-50"
                      >
                        {t('approval.approve')}
                      </button>
                      <button
                        type="button"
                        disabled={actingId !== null}
                        onClick={() => handleReject(l.id)}
                        className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:opacity-50"
                      >
                        {t('approval.reject')}
                      </button>
                    </div>
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
