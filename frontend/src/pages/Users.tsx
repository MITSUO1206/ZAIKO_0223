import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface UserRow {
  id: string
  login_id: string
  name: string
  role: string
}

const roleKey: Record<string, string> = {
  USER: 'users.roleUser',
  APPROVER: 'users.roleApprover',
  ADMIN: 'users.roleAdmin',
}

export default function Users() {
  const { t } = useTranslation()
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data } = await api.get<UserRow[]>('/users')
      return data
    },
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">{t('users.title')}</h1>
      {isLoading ? (
        <p>読み込み中...</p>
      ) : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('users.loginId')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('users.name')}</th>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{t('users.role')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">{u.login_id}</td>
                  <td className="px-4 py-2">{u.name}</td>
                  <td className="px-4 py-2">{t(roleKey[u.role] ?? u.role)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
