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
        'wm-bg': '#0a0a0f',
        'wm-panel': '#12121a',
        'wm-border': '#1a1a25',
        'wm-accent': '#3b82f6',
        'wm-accent-hover': '#2563eb',
        'wm-warning': '#f59e0b',
        'wm-danger': '#ef4444',
        'wm-success': '#22c55e',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
