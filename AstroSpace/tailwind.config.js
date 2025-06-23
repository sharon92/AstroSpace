/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./templates/**/*.html",
      "./static/**/*.js",
      "./**/*.html"
    ],
    theme: {
      extend: {
        fontFamily: {
          scribble: ['scribble', 'lato-hairline', 'sans-serif'],
          'lato-hairline': ['lato-hairline', 'sans-serif'],  
        }
      }
    },
    plugins: []
  };