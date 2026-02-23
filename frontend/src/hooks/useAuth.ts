import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export interface UserMe {
  id: string
  login_id: string
  name: string
  role: string
}

export function useAuth() {
  const token = localStorage.getItem('token')
  const { data: me, isLoading } = useQuery({
    queryKey: ['me', token],
    queryFn: async () => {
      const { data } = await api.get<UserMe>('/auth/me')
      return data
    },
    enabled: !!token,
    retry: false,
  })
  return { token, me, isLoading }
}
