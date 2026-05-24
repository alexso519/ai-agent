import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{ts,tsx}',
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          bg: '#f8fafc',
          grid: '#e2e8f0',
        },
      },
    },
  },
  plugins: [],
};

export default config;