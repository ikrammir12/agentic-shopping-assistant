
import { NavLink, Routes, Route } from 'react-router'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ChatPage from './pages/ChatPage'

import ProtectedRoute from './components/ProtectedRoute'

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-violet-700">
          {title}
        </h1>

        <p className="mt-2 text-slate-500">
          This page will be developed in the next steps.
        </p>

        <NavLink
          to="/"
          className="mt-5 inline-block text-violet-600"
        >
          Back to AI Assistant
        </NavLink>
      </div>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />

      <Route path="/login" element={<LoginPage />} />

      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/favorites"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Favorites" />
          </ProtectedRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <PlaceholderPage title="Profile" />
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={<PlaceholderPage title="Page not found" />}
      />
    </Routes>
  )
}

export default App
