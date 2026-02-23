import { api } from './client'

export type LedgerType = 'INBOUND' | 'OUTBOUND' | 'ISSUE'
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface Ledger {
  id: string
  item_id: string
  ledger_type: LedgerType
  quantity: number
  status: ApprovalStatus
  created_by: string
  created_at: string | null
  updated_at: string | null
  notes: string | null
}

export interface LedgerCreate {
  item_id: string
  ledger_type: LedgerType
  quantity: number
  notes?: string | null
}

export interface LedgerUpdate {
  item_id?: string
  ledger_type?: LedgerType
  quantity?: number
  notes?: string | null
}

export const ledgersApi = {
  list: (params?: { q?: string; status?: ApprovalStatus; item_id?: string }) =>
    api.get<Ledger[]>('/ledgers', { params }).then((r) => r.data),
  get: (id: string) => api.get<Ledger>(`/ledgers/${id}`).then((r) => r.data),
  create: (body: LedgerCreate) => api.post<Ledger>('/ledgers', body).then((r) => r.data),
  update: (id: string, body: LedgerUpdate) => api.patch<Ledger>(`/ledgers/${id}`, body).then((r) => r.data),
  withdraw: (id: string) => api.post(`/ledgers/${id}/withdraw`),
  pending: () => api.get<Ledger[]>('/ledgers/approval/pending').then((r) => r.data),
  approve: (id: string, body?: { comment?: string }) =>
    api.post<Ledger>(`/ledgers/${id}/approve`, body ?? {}).then((r) => r.data),
  reject: (id: string, body?: { comment?: string }) =>
    api.post<Ledger>(`/ledgers/${id}/reject`, body ?? {}).then((r) => r.data),
}
