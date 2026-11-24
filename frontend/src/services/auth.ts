
export type RegisterResponse = {
  message: string
  user: unknown
}

export async function registerUser(
  email: string,
  password: string
): Promise<RegisterResponse> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : 'Registration failed. Please try again.'

    throw new Error(detail)
  }

  return data as RegisterResponse
}

export type LoginResponse = {
  access_token: string
  token_type: string
  user: unknown
}

export async function loginUser(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : 'Login failed. Please try again.'

    throw new Error(detail)
  }

  return data as LoginResponse
}

export async function verifyToken(
  token: string
): Promise<boolean> {
  const response = await fetch('/api/auth/verify', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (response.status === 401 || response.status === 403) {
    return false
  }

  if (!response.ok) {
    throw new Error('Unable to verify authentication.')
  }

  const data = await response.json()

  return data.authenticated === true
}
