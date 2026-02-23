import { useEffect } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface Item {
  id: string
  code: string
  name: string
}

const schema = z.object({
  item_id: z.string().min(1, '品目を選択してください'),
  ledger_type: z.enum(['INBOUND', 'OUTBOUND', 'ISSUE', 'DISPOSAL']),
  quantity: z.coerce.number().int().min(1, '数量は1以上で入力してください'),
  lot: z.string().optional(),
  process_name: z.string().optional(),
  notes: z.string().optional(),
})

type Form = z.infer<typeof schema>

export default function LedgerForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const presetItemId = searchParams.get('item_id') ?? undefined
  const { t } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = !!id
  const { data: items = [] } = useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const { data } = await api.get<Item[]>('/items')
      return data
    },
  })
  const { data: ledger } = useQuery({
    queryKey: ['ledger', id],
    queryFn: async () => {
      const { data } = await api.get<Form & { id: string }>(`/ledgers/${id}`)
      return data
    },
    enabled: isEdit,
  })
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: {
      item_id: presetItemId ?? '',
      ledger_type: 'INBOUND',
      quantity: 1,
      lot: '',
      process_name: '',
    },
  })
  const createMutation = useMutation({
    mutationFn: (body: Form) => api.post('/ledgers', body),
    onSuccess: (_data, body) => {
      qc.invalidateQueries({ queryKey: ['ledgers'] })
      if (presetItemId) {
        qc.invalidateQueries({ queryKey: ['ledgers', 'item', presetItemId] })
        navigate(`/items/${presetItemId}/ledger`)
      } else {
        navigate('/ledgers')
      }
    },
  })
  const updateMutation = useMutation({
    mutationFn: (body: Form) => api.patch(`/ledgers/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ledgers'] }); qc.invalidateQueries({ queryKey: ['ledger', id] })
      navigate(`/ledgers/${id}`)
    },
  })

  useEffect(() => {
    if (ledger) reset({ item_id: ledger.item_id, ledger_type: ledger.ledger_type as Form['ledger_type'], quantity: ledger.quantity, lot: ledger.lot ?? '', process_name: ledger.process_name ?? '', notes: ledger.notes ?? '' })
  }, [ledger, reset])
  useEffect(() => {
    if (!isEdit && presetItemId) reset((prev) => ({ ...prev, item_id: presetItemId }))
  }, [presetItemId, isEdit, reset])

  const onSubmit = (data: Form) => {
    const payload = { ...data, notes: data.notes || null, lot: data.lot || null, process_name: data.process_name || null }
    if (isEdit) updateMutation.mutate(payload)
    else createMutation.mutate(payload)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{isEdit ? t('ledgers.edit') : t('ledgers.new')}</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded shadow p-6 max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('ledgers.item')}</label>
          <select
            {...register('item_id')}
            className="w-full border border-gray-300 rounded px-3 py-2"
            disabled={isEdit}
          >
            <option value="">選択してください</option>
            {items.map((i) => (
              <option key={i.id} value={i.id}>{i.code} - {i.name}</option>
            ))}
          </select>
          {errors.item_id && <p className="text-red-500 text-sm">{errors.item_id.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('ledgers.type')}</label>
          <select {...register('ledger_type')} className="w-full border border-gray-300 rounded px-3 py-2">
            <option value="INBOUND">{t('ledgers.typeInbound')}</option>
            <option value="OUTBOUND">{t('ledgers.typeOutbound')}</option>
            <option value="ISSUE">{t('ledgers.typeIssue')}</option>
            <option value="DISPOSAL">{t('ledgers.typeDisposal')}</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('ledgers.lot')}</label>
          <input {...register('lot')} className="w-full border border-gray-300 rounded px-3 py-2" placeholder="任意" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('ledgers.processName')}</label>
          <input {...register('process_name')} className="w-full border border-gray-300 rounded px-3 py-2" placeholder="払い出し時" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('ledgers.quantity')}</label>
          <input
            type="number"
            min={1}
            {...register('quantity')}
            className="w-full border border-gray-300 rounded px-3 py-2"
          />
          {errors.quantity && <p className="text-red-500 text-sm">{errors.quantity.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.notes')}</label>
          <textarea {...register('notes')} className="w-full border border-gray-300 rounded px-3 py-2" rows={3} />
        </div>
        <div className="flex gap-2">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {isEdit ? t('items.update') : t('items.create')}
          </button>
          <Link to={isEdit ? `/ledgers/${id}` : '/ledgers'} className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('common.cancel')}
          </Link>
        </div>
      </form>
    </div>
  )
}
