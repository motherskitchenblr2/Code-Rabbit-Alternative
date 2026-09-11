import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type Theme = 'dark' | 'light'
type Accent = 'magenta' | 'cyan' | 'amber' | 'green'

interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  accent: Accent
  setAccent: (accent: Accent) => void
}

const ACCENTS: Accent[] = ['magenta', 'cyan', 'amber', 'green']

function readStorage<T extends string>(key: string, fallback: T, valid: readonly T[]): T {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(key) as T | null
    if (stored && valid.includes(stored)) return stored
  }
  return fallback
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme') as Theme | null
      if (stored) return stored
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'dark'
  })

  const [accent, setAccentState] = useState<Accent>(() => readStorage('accent', 'magenta', ACCENTS))

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('dark', 'light')
    root.classList.add(theme)
    localStorage.setItem('theme', theme)
    root.dataset.accent = accent
    localStorage.setItem('accent', accent)
  }, [theme, accent])

  const toggleTheme = () => {
    setThemeState(prev => prev === 'dark' ? 'light' : 'dark')
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  const setAccent = (newAccent: Accent) => {
    setAccentState(newAccent)
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme, accent, setAccent }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}