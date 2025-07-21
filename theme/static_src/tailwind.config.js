// tailwind.config.js
module.exports = {
  content: [
    '../templates/**/*.{html,js,py}',   // ← your Django templates
    './src/**/*.{js,jsx,ts,tsx,html}',  // ← any JS/React files
  ],
  safelist: [{ pattern: /.*/ }],        // if you really want _every_ class
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
