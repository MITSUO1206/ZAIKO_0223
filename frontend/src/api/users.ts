import { api } from './client'

export interface User {
  id: string
  login_id: string
  name: string
  role: string
}

export const usersApi = {
  list: () => api.get<User[]>('/users').then((r) => r.data),
}
