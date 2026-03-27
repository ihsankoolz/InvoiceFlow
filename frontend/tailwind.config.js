/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        body: ['Lato', 'sans-serif'],
      },
      colors: {
        cream: '#fff8ec',
        ink: '#222222',
        teal: '#1c3f3a',
        slate: '#303437',
        orange: '#ff9500',
        green: '#3e9b00',
      },
    },
  },
  plugins: [],
}
