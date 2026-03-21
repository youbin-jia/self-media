import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import { ThemeProvider, useThemeMode } from './context/ThemeContext'
import './index.css'

function AppWithTheme() {
  const { themeMode } = useThemeMode()
  const isDark = themeMode === 'dark'

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#6D5EF5',
          colorInfo: '#6D5EF5',
          colorSuccess: '#22c55e',
          colorWarning: '#f59e0b',
          borderRadius: 14,
          borderRadiusLG: 18,
          boxShadowTertiary: '0 14px 30px rgba(15, 23, 42, 0.08)'
        },
        components: {
          Card: {
            borderRadiusLG: 18
          },
          Button: {
            borderRadius: 12,
            controlHeight: 38
          },
          Table: {
            headerBg: isDark ? '#161b2f' : '#f8f9ff',
            rowHoverBg: isDark ? '#141b2f' : '#f5f6ff'
          }
        }
      }}
    >
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AppWithTheme />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
)
