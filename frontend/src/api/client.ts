import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // Send HttpOnly cookies with requests
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

let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && accessToken && !error.config._retry) {
      error.config._retry = true

      // Deduplicate concurrent refresh requests
      if (!isRefreshing) {
        isRefreshing = true
        refreshPromise = axios
          .post(`${API_BASE}/auth/refresh/`, {}, { withCredentials: true })
          .then((res) => res.data.access as string)
          .catch(() => null)
          .finally(() => { isRefreshing = false })
      }

      const newAccess = await refreshPromise
      if (newAccess) {
        setAccessToken(newAccess)
        error.config.headers.Authorization = `Bearer ${newAccess}`
        return axios(error.config)
      }

      // Refresh failed
      setAccessToken(null)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
