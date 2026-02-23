import { api } from './client'

export interface Item {
  id: string
  code: string
  name: string
  current_qty: number
  deleted_at: string | null
  notes: string | null
}

export interface ItemCreate {
  code: string
  name: string
  notes?: string | null
}

export interface ItemUpdate {
  code?: string
  name?: string
  notes?: string | null
}

export const itemsApi = {
  list: (params?: { q?: string; include_deleted?: boolean }) =>
    api.get<Item[]>('/items', { params }).then((r) => r.data),
  get: (id: string) => api.get<Item>(`/items/${id}`).then((r) => r.data),
  create: (body: ItemCreate) => api.post<Item>('/items', body).then((r) => r.data),
  update: (id: string, body: ItemUpdate) => api.patch<Item>(`/items/${id}`, body).then((r) => r.data),
  delete: (id: string) => api.delete(`/items/${id}`),
}
