import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { loginUser } from '../services/auth'

function LoginPage() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    try {
      setLoading(true)

      const result = await loginUser(email, password)

      localStorage.setItem('access_token', result.access_token)

      navigate('/')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-violet-700">
            Blink AI
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Your personal AI shopping assistant
          </p>
        </div>

        <h2 className="text-2xl font-bold text-slate-900">
          Welcome back
        </h2>

        <p className="mt-2 text-sm text-slate-500">
          Sign in to continue with Blink AI.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-violet-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-violet-500"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-violet-600 py-3 font-semibold text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>

        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Don't have an account?{' '}
          <Link to="/register" className="font-semibold text-violet-600">
            Create account
          </Link>
        </p>

      </div>
    </div>
  )
}

export default LoginPage