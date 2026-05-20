export const colors = {
  primary: {
    50: '#FAF8F4',
    100: '#F3EFE5',
    200: '#E8DFC8',
    300: '#D4B896',
    400: '#C8A96E',
    500: '#B89455',
    600: '#9E7E45',
    700: '#7D6336',
    800: '#5C4928',
    900: '#3D311B',
  },
  carnerf: {
    dark: '#000000',
    card: '#0a0a0a',
    bg: '#07090F',
    nav: '#0E1117',
    accent: '#C8A96E',
  },
  border: 'rgba(255,255,255,0.08)',
  text: '#FFFFFF',
  sub: '#9CA3AF',
  dim: '#6B7280',
} as const;

export const ACCENT = colors.carnerf.accent;
export const BG = colors.carnerf.dark;
export const CARD = colors.carnerf.nav;
