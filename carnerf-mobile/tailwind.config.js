/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#000000',
          deep: '#07090F',
          card: '#0E1117',
          surface: '#0a0a0a',
        },
        gold: {
          50: '#FAF8F4',
          100: '#F5F0E6',
          200: '#E8DCC1',
          300: '#DAC79C',
          400: '#C8A96E',
          500: '#B89456',
          600: '#9A7A42',
          700: '#7A6034',
          800: '#5A4626',
          900: '#3D311B',
        },
        ink: {
          DEFAULT: '#FFFFFF',
          soft: '#E5E7EB',
          mute: '#9CA3AF',
          dim: '#6B7280',
        },
      },
      fontFamily: {
        sans: ['Pretendard', 'System'],
      },
    },
  },
  plugins: [],
};
