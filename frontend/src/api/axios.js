import axios from 'axios'

const TOKEN_KEY = 'invoiceflow_token'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Attach Authorization header on every request if a token exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

export default api
