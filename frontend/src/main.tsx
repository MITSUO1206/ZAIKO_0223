import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ja from './locales/ja.json'
import App from './App'
import './index.css'

i18n.use(initReactI18next).init({
  resources: { ja: { translation: ja } },
  lng: 'ja',
  fallbackLng: 'ja',
  interpolation: { escapeValue: false },
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 0 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
