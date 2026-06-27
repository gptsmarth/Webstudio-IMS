export interface AppTheme {
  colors: {
    background: string;
    text: string;
    muted: string;
    primary: string;
  };
}

export function getTheme(scheme: 'light' | 'dark' | null | undefined): AppTheme {
  if (scheme === 'dark') {
    return {
      colors: {
        background: '#0f172a',
        text: '#f8fafc',
        muted: '#94a3b8',
        primary: '#38bdf8',
      },
    };
  }

  return {
    colors: {
      background: '#ffffff',
      text: '#0f172a',
      muted: '#64748b',
      primary: '#0284c7',
    },
  };
}
