import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'

interface Ledger {
  id: string
  item_id: string
  ledger_type: string
  quantity: number
  status: string
  created_by: string
  created_at: string
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

export default function LedgerDetail() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const { me } = useAuth()
  const qc = useQueryClient()
  const { data: ledger, isLoading } = useQuery({
    queryKey: ['ledger', id],
    queryFn: async () => {
      const { data } = await api.get<Ledger>(`/ledgers/${id}`)
      return data
    },
    enabled: !!id,
  })
  const withdrawMutation = useMutation({
    mutationFn: () => api.post(`/ledgers/${id}/withdraw`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledgers'] }); qc.invalidateQueries({ queryKey: ['ledger', id] })
    },
  })

  if (!id) return null
  if (isLoading || !ledger) return <p>読み込み中...</p>

  const canEdit = ledger.status === 'PENDING' && ledger.created_by === me?.id
  const canWithdraw = ledger.status === 'PENDING' && ledger.created_by === me?.id

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{t('ledgers.detail')}</h1>
        <div className="flex gap-2">
          {canEdit && (
            <Link to={`/ledgers/${id}/edit`} className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
              {t('ledgers.edit')}
            </Link>
          )}
          {canWithdraw && (
            <button
              type="button"
              onClick={() => window.confirm('取下げしますか？') && withdrawMutation.mutate()}
              className="bg-amber-100 text-amber-800 px-4 py-2 rounded hover:bg-amber-200"
            >
              {t('ledgers.withdraw')}
            </button>
          )}
          <Link to="/ledgers" className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('items.back')}
          </Link>
        </div>
      </div>
      <div className="bg-white rounded shadow p-6 max-w-md">
        <dl className="space-y-2">
          <div>
            <dt className="text-sm text-gray-500">ID</dt>
            <dd className="font-mono">{ledger.id}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">{t('ledgers.item')}</dt>
            <dd>{ledger.item_id}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">{t('ledgers.type')}</dt>
            <dd>{t(typeKey[ledger.ledger_type] ?? ledger.ledger_type)}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">{t('ledgers.quantity')}</dt>
            <dd>{ledger.quantity}</dd>
          </div>
          {(ledger as Record<string, unknown>).lot && (
            <div>
              <dt className="text-sm text-gray-500">{t('ledgers.lot')}</dt>
              <dd>{(ledger as Record<string, unknown>).lot as string}</dd>
            </div>
          )}
          {(ledger as Record<string, unknown>).process_name && (
            <div>
              <dt className="text-sm text-gray-500">{t('ledgers.processName')}</dt>
              <dd>{(ledger as Record<string, unknown>).process_name as string}</dd>
            </div>
          )}
          <div>
            <dt className="text-sm text-gray-500">{t('ledgers.status')}</dt>
            <dd>{t(statusKey[ledger.status] ?? ledger.status)}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">{t('ledgers.createdBy')}</dt>
            <dd>{ledger.created_by}</dd>
          </div>
          {ledger.notes && (
            <div>
              <dt className="text-sm text-gray-500">{t('items.notes')}</dt>
              <dd>{ledger.notes}</dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  )
}
