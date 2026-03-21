import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const ThemeContext = createContext({
  themeMode: 'light',
  setThemeMode: () => {}
})

const STORAGE_KEY = 'self-media-theme-mode'

export function ThemeProvider({ children }) {
  const [themeMode, setThemeMode] = useState(() => {
    const cached = localStorage.getItem(STORAGE_KEY)
    return cached === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, themeMode)
  }, [themeMode])

  const value = useMemo(() => ({ themeMode, setThemeMode }), [themeMode])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useThemeMode() {
  return useContext(ThemeContext)
}

