// tailwind.config.js
module.exports = {
  content: [
    './templates/**/*.html',
    './theme/templates/**/*.html',
    './*/templates/**/*.html',
  ],
  // put back preflight so you get sensible base styles
  corePlugins: {
    preflight: true,
  },
  safelist: [
    // If you still need to guarantee some classes, you can list them here.
    // But in most cases, just correctly pointing at your HTML is enough.
    'bg-gray-800',
    'text-white',
    'flex', 'items-center', 'justify-between', 'hidden', 'block', 
    'md:flex', 'md:hidden', 'max-w-7xl', 'mx-auto',
    'px-4','sm:px-6','lg:px-8','h-16','p-2','rounded',
    'hover:bg-gray-700','focus:outline-none','h-6','w-6','fill-current',
    'border-t','border-gray-600','mt-2','relative','absolute','pl-4'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
