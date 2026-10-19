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
          bg: '#070b14',
          panel: '#0d1424',
          card: '#131d33',
          border: '#1c2740',
          text: '#e6ecff',
          muted: '#8b97b8',
        },
        bank: {
          sre: '#00ff88',
          sec: '#ff0055',
          hud: '#00f0ff',
          res: '#b000ff',
          gen: '#ffaa00',
        }
      },
      fontFamily: {
        mono: ['Fira Code', 'JetBrains Mono', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'neon-hud': '0 0 15px rgba(0, 240, 255, 0.4)',
        'neon-sre': '0 0 15px rgba(0, 255, 136, 0.4)',
        'neon-sec': '0 0 15px rgba(255, 0, 85, 0.4)',
      }
    },
  },
  plugins: [],
}
