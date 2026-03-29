import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && accessToken) {
      // Try to refresh
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const res = await axios.post('/api/auth/refresh/', { refresh: refreshToken })
          const newAccess = res.data.access
          setAccessToken(newAccess)
          error.config.headers.Authorization = `Bearer ${newAccess}`
          return axios(error.config)
        } catch {
          // Refresh failed, clear tokens
          setAccessToken(null)
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
