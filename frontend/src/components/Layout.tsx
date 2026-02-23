import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { t } = useTranslation()
  const { me } = useAuth()
  const navigate = useNavigate()

  const logout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex gap-6">
            <Link to="/items" className="text-gray-700 hover:text-gray-900 font-medium">
              {t('nav.items')}
            </Link>
            <Link to="/ledgers" className="text-gray-700 hover:text-gray-900 font-medium">
              {t('nav.ledgers')}
            </Link>
            {(me?.role === 'APPROVER' || me?.role === 'ADMIN') && (
              <Link to="/approval" className="text-gray-700 hover:text-gray-900 font-medium">
                {t('nav.approval')}
              </Link>
            )}
            {me?.role === 'ADMIN' && (
              <Link to="/users" className="text-gray-700 hover:text-gray-900 font-medium">
                {t('nav.users')}
              </Link>
            )}
            <Link to="/reports" className="text-gray-700 hover:text-gray-900 font-medium">
              {t('nav.reports')}
            </Link>
            <Link to="/alerts" className="text-gray-700 hover:text-gray-900 font-medium">
              {t('nav.alerts')}
            </Link>
            <Link to="/chat" className="text-gray-700 hover:text-gray-900 font-medium">
              {t('nav.chat')}
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{me?.name} ({me?.role})</span>
            <button
              type="button"
              onClick={logout}
              className="text-sm text-red-600 hover:text-red-800"
            >
              {t('nav.logout')}
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
