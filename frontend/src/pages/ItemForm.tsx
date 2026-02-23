import { useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

const schema = z.object({
  code: z.string().min(1, '品目コードを入力してください'),
  name: z.string().min(1, '品目名を入力してください'),
  model_number: z.string().optional(),
  category: z.string().optional(),
  unit: z.string().optional(),
  unit_price: z.coerce.number().optional(),
  safety_stock: z.coerce.number().int().min(0).optional(),
  storage_place: z.string().optional(),
  current_qty: z.coerce.number().int().min(0).optional(),
  last_lot: z.string().optional(),
  last_inbound_qty: z.coerce.number().int().min(0).optional(),
  last_inbound_date: z.string().optional(),
  notes: z.string().optional(),
})

type Form = z.infer<typeof schema>

export default function ItemForm() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isEdit = !!id
  const { data: item } = useQuery({
    queryKey: ['item', id],
    queryFn: async () => {
      const { data } = await api.get<Form & { id: string }>(`/items/${id}`)
      return data
    },
    enabled: isEdit,
  })
  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  })
  useEffect(() => {
    if (item) {
      const i = item as Record<string, unknown>
      reset({
        code: item.code,
        name: item.name,
        model_number: i.model_number ?? '',
        category: i.category ?? '',
        unit: i.unit ?? '',
        unit_price: i.unit_price ?? undefined,
        safety_stock: i.safety_stock ?? 0,
        storage_place: i.storage_place ?? '',
        current_qty: i.current_qty ?? 0,
        last_lot: i.last_lot ?? '',
        last_inbound_qty: i.last_inbound_qty ?? undefined,
        last_inbound_date: i.last_inbound_date ? String(i.last_inbound_date).slice(0, 10) : '',
        notes: item.notes ?? '',
      })
    }
  }, [item, reset])
  const createMutation = useMutation({
    mutationFn: (body: Form) => api.post('/items', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
      navigate('/items')
    },
  })
  const updateMutation = useMutation({
    mutationFn: (body: Form) => api.patch(`/items/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] }); qc.invalidateQueries({ queryKey: ['item', id] })
      navigate(`/items/${id}`)
    },
  })

  const onSubmit = (data: Form) => {
    const payload = {
      ...data,
      notes: data.notes || null,
      model_number: data.model_number || null,
      category: data.category || null,
      unit: data.unit || null,
      unit_price: data.unit_price ?? null,
      safety_stock: data.safety_stock ?? 0,
      storage_place: data.storage_place || null,
      last_lot: data.last_lot || null,
      last_inbound_qty: data.last_inbound_qty ?? null,
      last_inbound_date: data.last_inbound_date || null,
    }
    if (isEdit) {
      const updatePayload = { ...payload, current_qty: data.current_qty ?? 0 }
      updateMutation.mutate(updatePayload)
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{isEdit ? t('items.edit') : t('items.new')}</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded shadow p-6 max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.code')}</label>
          <input
            {...register('code')}
            className="w-full border border-gray-300 rounded px-3 py-2"
            readOnly={isEdit}
          />
          {errors.code && <p className="text-red-500 text-sm">{errors.code.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.name')}</label>
          <input {...register('name')} className="w-full border border-gray-300 rounded px-3 py-2" />
          {errors.name && <p className="text-red-500 text-sm">{errors.name.message}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.modelNumber')}</label>
          <input {...register('model_number')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.category')}</label>
          <input {...register('category')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.unit')}</label>
          <input {...register('unit')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.unitPrice')}</label>
          <input type="number" step="0.01" {...register('unit_price')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.safetyStock')}</label>
          <input type="number" min={0} {...register('safety_stock')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.storagePlace')}</label>
          <input {...register('storage_place')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.lastLot')}</label>
          <input {...register('last_lot')} className="w-full border border-gray-300 rounded px-3 py-2" placeholder="LOT番号" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.lastInboundQty')}</label>
          <input type="number" min={0} {...register('last_inbound_qty')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.lastInboundDate')}</label>
          <input type="date" {...register('last_inbound_date')} className="w-full border border-gray-300 rounded px-3 py-2" />
        </div>
        {isEdit && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.currentQty')}</label>
            <input type="number" min={0} {...register('current_qty')} className="w-full border border-gray-300 rounded px-3 py-2" />
            <p className="text-xs text-gray-500 mt-0.5">自由に増減できます</p>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t('items.notes')}</label>
          <textarea {...register('notes')} className="w-full border border-gray-300 rounded px-3 py-2" rows={3} />
        </div>
        <div className="flex gap-2">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {isEdit ? t('items.update') : t('items.create')}
          </button>
          <Link to={isEdit ? `/items/${id}` : '/items'} className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">
            {t('common.cancel')}
          </Link>
        </div>
      </form>
    </div>
  )
}
