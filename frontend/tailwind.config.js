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
          50: '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          900: '#312e81',
        },
        clinical: {
          critical: '#ef4444',
          high: '#f97316',
          medium: '#eab308',
          info: '#3b82f6',
          success: '#10b981'
        }
      }
    },
  },
  plugins: [],
}
