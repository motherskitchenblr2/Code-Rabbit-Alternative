/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          900: '#0a0a0f',
          800: '#1a1a2e',
          700: '#16213e',
          600: '#0f3460',
          500: '#1e4d92',
          400: '#2a6fc4',
          300: '#3a9cff',
          200: '#5aBDFF',
          100: '#8adeff',
          50: '#c6ffff',
        },
        neon: {
          magenta: '#ff00ff',
          cyan: '#00ffff',
          amber: '#ff8c00',
          green: '#00ff00',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
        display: ['Orbitron', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(255, 0, 255, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(0, 255, 255, 0.5)' },
        },
      },
    },
  },
  plugins: [],
}