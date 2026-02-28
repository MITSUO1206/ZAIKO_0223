import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

export default function Chat() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const promptFromUrl = searchParams.get('prompt') || searchParams.get('q') || ''
  const [query, setQuery] = useState(promptFromUrl)
  const [result, setResult] = useState<{ answer: string; links: Array<{ type: string; id: string; label: string }> } | null>(null)
  const autoSubmitted = useRef(false)
  const geminiStatusMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.get<{ connected: boolean; message: string; key_configured?: boolean; key_suffix?: string }>('/chat/gemini-status')
      return data
    },
  })
  const mutation = useMutation({
    mutationFn: async (q: string) => {
      const { data } = await api.post<{ answer: string; links: Array<{ type: string; id: string; label: string }> }>('/chat/query', { query: q })
      return data
    },
    onSuccess: (data) => setResult(data),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) mutation.mutate(query.trim())
  }

  // 集計画面から「チャットで傾向を聞く」で飛んできたとき: プロンプトを入れて1回だけ自動送信
  useEffect(() => {
    const q = promptFromUrl.trim()
    if (q && !autoSubmitted.current) {
      autoSubmitted.current = true
      setQuery(q)
      mutation.mutate(q)
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 初回URLプロンプトのみ自動送信
  }, [promptFromUrl])

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{t('chat.title')}</h1>
        <button
          type="button"
          onClick={() => geminiStatusMutation.mutate()}
          disabled={geminiStatusMutation.isPending}
          className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
        >
          {geminiStatusMutation.isPending ? '確認中...' : 'Gemini API 接続確認'}
        </button>
      </div>
      {geminiStatusMutation.data && (
        <div
          className={`mb-4 px-3 py-2 rounded text-sm ${geminiStatusMutation.data.connected ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}
        >
          <div>{geminiStatusMutation.data.connected ? '✓ ' + geminiStatusMutation.data.message : '✗ ' + geminiStatusMutation.data.message}</div>
          {!geminiStatusMutation.data.connected && geminiStatusMutation.data.key_configured === false && (
            <div className="mt-2 text-xs opacity-90">※ キーがバックエンドに届いていません（.env の場所・Docker の env_file を確認）</div>
          )}
          {!geminiStatusMutation.data.connected && geminiStatusMutation.data.key_configured === true && (
            <div className="mt-2 text-xs opacity-90">※ キーは届いていますが Google が無効と判定しています。別のキーを発行して試してください。</div>
          )}
          {geminiStatusMutation.data.key_suffix && (
            <div className="mt-2 text-xs opacity-90">バックエンドが読んだキー末尾: ****{geminiStatusMutation.data.key_suffix}（.env の末尾と一致すれば同じキーです）</div>
          )}
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('chat.placeholder')}
          className="flex-1 border border-gray-300 rounded px-3 py-2"
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">{t('chat.send')}</button>
      </form>
      {result && (
        <div>
          <p className="mb-4">{result.answer}</p>
          <ul className="space-y-2">
            {result.links.map((l) => (
              <li key={`${l.type}-${l.id}`}>
                <Link to={l.type === 'item' ? `/items/${l.id}` : `/ledgers/${l.id}`} className="text-blue-600 hover:underline">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
