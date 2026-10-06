/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        aiDark: '#060B1E',
        aiNavy: '#0B1437',
        aiSurface: '#111C44',
        aiCard: 'rgba(15, 26, 68, 0.75)',
        aiCyan: '#00F5D4',
        aiTeal: '#00F2FE',
        aiBlue: '#3B82F6',
        aiPurple: '#7928CA',
        aiText: '#E2E8F0',
        aiMuted: '#94A3B8',
        brand: {
          50: '#F0F9FF',
          100: '#E0F2FE',
          200: '#BAE6FD',
          300: '#7DD3FC',
          400: '#38BDF8',
          500: '#00F5D4',
          600: '#0284C7',
          700: '#0369A1',
          800: '#0B1437',
          900: '#060B1E',
          950: '#030611',
        },
        sand: {
          50: '#FAF9F6',
          100: '#F5F3ED',
          200: '#EAE6DB',
          300: '#DCD4C3',
        },
        accent: {
          gold: '#C59B27',
          goldLight: '#FBF5E6',
          goldDark: '#997315',
        }
      },
      fontFamily: {
        arabic: ['"IBM Plex Sans Arabic"', 'Tajawal', 'Cairo', 'Alexandria', 'sans-serif'],
      },
      boxShadow: {
        'subtle': '0 2px 10px rgba(0, 0, 0, 0.03), 0 1px 3px rgba(0, 0, 0, 0.05)',
        'premium': '0 10px 30px -10px rgba(0, 245, 212, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
        'glow-cyan': '0 0 25px rgba(0, 245, 212, 0.35)',
        'glow-teal': '0 0 25px rgba(0, 242, 254, 0.35)',
        'glow-purple': '0 0 35px rgba(121, 40, 202, 0.4)',
        'float': '0 20px 40px -15px rgba(6, 11, 30, 0.6)',
      }
    },
  },
  plugins: [],
}
