/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "mlb-dark": "#0f172a",
        "mlb-card": "#1e293b",
        "mlb-green": "#22c55e",
        "mlb-red": "#ef4444",
      }
    },
  },
  plugins: [],
}