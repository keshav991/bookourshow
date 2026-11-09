/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fff1f2',
          100: '#ffe4e6',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
          900: '#881337',
        },
        cinema: {
          dark: '#0b0f19',
          card: '#151d2f',
          input: '#1a243b',
          border: '#2a3754',
          accent: '#e11d48',
        }
      }
    },
  },
  plugins: [],
}
