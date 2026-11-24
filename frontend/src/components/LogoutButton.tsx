import { useNavigate } from 'react-router'

function LogoutButton() {
  const navigate = useNavigate()

  function handleLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('blink_ai_messages')
  localStorage.removeItem('blink_ai_conversation_id')

  navigate('/login', { replace: true })
}
  return (
    <button
      onClick={handleLogout}
      className="w-full rounded-lg px-4 py-3 text-left text-sm font-medium text-slate-600 transition hover:bg-red-50 hover:text-red-600"
    >
      Log out
    </button>
  )
}

export default LogoutButton