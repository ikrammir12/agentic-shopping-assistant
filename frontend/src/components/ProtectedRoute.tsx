import { useEffect, useState, type ReactNode } from 'react'
import { Navigate } from 'react-router'
import { verifyToken } from '../services/auth'

type AuthStatus = 'checking' | 'allowed' | 'denied' | 'error'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('checking')

  useEffect(() => {
    let active = true

    async function checkAuthentication() {
      const token = localStorage.getItem('access_token')

      if (!token) {
        setStatus('denied')
        return
      }

      setStatus('checking')

      try {
        const isValid = await verifyToken(token)

        if (!active) return

        if (isValid) {
          setStatus('allowed')
        } else {
          localStorage.removeItem('access_token')
          setStatus('denied')
        }
      } catch {
        if (active) {
          setStatus('error')
        }
      }
    }

    function handleWindowFocus() {
      void checkAuthentication()
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        void checkAuthentication()
      }
    }

    function handleStorageChange() {
      void checkAuthentication()
    }

    // Check when the component first loads.
    void checkAuthentication()

    // Check again when the user returns to the application.
    window.addEventListener('focus', handleWindowFocus)
    window.addEventListener('storage', handleStorageChange)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      active = false

      window.removeEventListener('focus', handleWindowFocus)
      window.removeEventListener('storage', handleStorageChange)
      document.removeEventListener(
        'visibilitychange',
        handleVisibilityChange
      )
    }
  }, [])

  if (status === 'checking') {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-600">
        Verifying your session...
      </div>
    )
  }

  if (status === 'denied') {
    return <Navigate to="/login" replace />
  }

  if (status === 'error') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-slate-700">
        <p>Unable to verify your session. Check that the backend is running.</p>

        <button
          onClick={() => window.location.reload()}
          className="rounded-lg bg-violet-600 px-5 py-2 text-white"
        >
          Retry
        </button>
      </div>
    )
  }

  return <>{children}</>
}

export default ProtectedRoute