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
        // Single font family 'Lato' for all weights and styles
        sans: ['Lato', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        scribble: ['scribble', 'sans-serif'],
        patung: ['Patung', 'sans-serif'],
      },
      fontWeight: {
        hairline: '100',
        thin: '200',
        light: '300',
        normal: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
        heavy: '800',
        black: '900',
      },
      transitionDuration: {
        '10000': '10000ms', // 10 seconds
      },
    },
  },
  plugins: [],
};
