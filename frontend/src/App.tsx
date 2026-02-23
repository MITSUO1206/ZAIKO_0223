import { Routes, Route, Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Layout from './components/Layout'
import Login from './pages/Login'
import Items from './pages/Items'
import ItemDetail from './pages/ItemDetail'
import ItemLedger from './pages/ItemLedger'
import ItemForm from './pages/ItemForm'
import Ledgers from './pages/Ledgers'
import LedgerDetail from './pages/LedgerDetail'
import LedgerForm from './pages/LedgerForm'
import Approval from './pages/Approval'
import Users from './pages/Users'
import Reports from './pages/Reports'
import Alerts from './pages/Alerts'
import Chat from './pages/Chat'
import { useAuth } from './hooks/useAuth'

function Protected({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  const { t } = useTranslation()
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/items" replace />} />
        <Route path="items" element={<Items />} />
        <Route path="items/new" element={<ItemForm />} />
        <Route path="items/:id" element={<ItemDetail />} />
        <Route path="items/:id/ledger" element={<ItemLedger />} />
        <Route path="items/:id/edit" element={<ItemForm />} />
        <Route path="ledgers" element={<Ledgers />} />
        <Route path="ledgers/new" element={<LedgerForm />} />
        <Route path="ledgers/:id" element={<LedgerDetail />} />
        <Route path="ledgers/:id/edit" element={<LedgerForm />} />
        <Route path="approval" element={<Approval />} />
        <Route path="users" element={<Users />} />
        <Route path="reports" element={<Reports />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="chat" element={<Chat />} />
      </Route>
      <Route path="*" element={<div className="p-4">{t('common.notFound')}</div>} />
    </Routes>
  )
}

export default App
