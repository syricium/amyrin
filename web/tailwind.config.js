/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/src/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#ffffff",
        special: "#75acff",
        secondary: "#1c1c1c",
        background: "#121212"
      }
    },
  },
  plugins: [],
}
