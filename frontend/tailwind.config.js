/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        court: {
          bg: '#080C14',
          surface: '#0F1520',
          border: '#1A2235',
          orange: '#FF7A00',
          amber: '#FFB347',
          green: '#00E87A',
          red: '#FF4444',
          muted: '#4A5568',
          text: '#E2E8F0',
          subtext: '#718096',
        }
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'sans-serif'],
        mono: ['"DM Mono"', 'monospace'],
        body: ['"Barlow"', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
