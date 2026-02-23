import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../api/client'

const schema = z.object({
  login_id: z.string().min(1, 'ログインIDを入力してください'),
  password: z.string().min(1, 'パスワードを入力してください'),
})

type Form = z.infer<typeof schema>

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: Form) => {
    setError('')
    try {
      const { data: res } = await api.post<{ access_token: string }>('/auth/login', data)
      localStorage.setItem('token', res.access_token)
      navigate('/items')
    } catch {
      setError(t('login.error'))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm">
        <h1 className="text-xl font-bold text-center mb-6">{t('login.title')}</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('login.loginId')}</label>
            <input
              {...register('login_id')}
              className="w-full border border-gray-300 rounded px-3 py-2"
              autoComplete="username"
            />
            {errors.login_id && (
              <p className="text-red-500 text-sm mt-1">{errors.login_id.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('login.password')}</label>
            <input
              {...register('password')}
              type="password"
              className="w-full border border-gray-300 rounded px-3 py-2"
              autoComplete="current-password"
            />
            {errors.password && (
              <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>
            )}
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            {t('login.submit')}
          </button>
        </form>
      </div>
    </div>
  )
}
