
module.exports = {
  content: [
    './templates/**/*.html',
    './static/src/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#10B981', // A modern, vibrant green
        secondary: '#F59E0B',
        accent: '#3B82F6',
      },
      animation: {
        'fade-in': 'fadeIn 1s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}
