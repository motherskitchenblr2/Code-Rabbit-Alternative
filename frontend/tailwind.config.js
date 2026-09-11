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
          900: 'rgb(var(--cyber-900) / <alpha-value>)',
          800: 'rgb(var(--cyber-800) / <alpha-value>)',
          700: 'rgb(var(--cyber-700) / <alpha-value>)',
          600: 'rgb(var(--cyber-600) / <alpha-value>)',
          500: 'rgb(var(--cyber-500) / <alpha-value>)',
          400: 'rgb(var(--cyber-400) / <alpha-value>)',
          300: 'rgb(var(--cyber-300) / <alpha-value>)',
          200: 'rgb(var(--cyber-200) / <alpha-value>)',
          100: 'rgb(var(--cyber-100) / <alpha-value>)',
          50: 'rgb(var(--cyber-50) / <alpha-value>)',
        },
        neon: {
          magenta: 'rgb(var(--accent) / <alpha-value>)',
          cyan: 'rgb(var(--neon-cyan) / <alpha-value>)',
          amber: 'rgb(var(--neon-amber) / <alpha-value>)',
          green: 'rgb(var(--neon-green) / <alpha-value>)',
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