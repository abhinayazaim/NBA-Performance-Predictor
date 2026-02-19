import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
window.onerror = (msg, src, line, col, err) => {
  document.body.innerHTML = `
    <div style="padding:40px;color:#ff4444;font-family:monospace;background:#080c14;min-height:100vh">
      <h2 style="color:#ff7a00">CRASH REPORT</h2>
      <p>${msg}</p>
      <p style="color:#666">at ${src}:${line}:${col}</p>
      <pre style="color:#aaa;font-size:11px;white-space:pre-wrap">${err?.stack || ''}</pre>
    </div>
  `
}
