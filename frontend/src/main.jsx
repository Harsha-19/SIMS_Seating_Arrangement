import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { StoreProvider } from './store'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <StoreProvider>
        <App />
      </StoreProvider>
    </ErrorBoundary>
  </StrictMode>,
)
