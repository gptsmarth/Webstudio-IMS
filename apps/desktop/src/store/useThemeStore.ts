import { create } from 'zustand';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeStore {
  theme: ThemeMode;
  resolvedTheme: 'light' | 'dark';
  isInitialized: boolean;
  setTheme: (theme: ThemeMode) => Promise<void>;
  toggleTheme: () => Promise<void>;
  initTheme: () => Promise<void>;
}

const resolveSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'dark';
};

const applyThemeClass = (mode: ThemeMode): 'light' | 'dark' => {
  const actual = mode === 'system' ? resolveSystemTheme() : mode;
  document.body.classList.remove('light', 'dark');
  document.body.classList.add(actual);
  return actual;
};

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: 'light',
  resolvedTheme: 'light',
  isInitialized: false,

  initTheme: async () => {
    let savedTheme: ThemeMode = 'light';
    try {
      if (window.config?.get) {
        const res = await window.config.get('theme');
        if (res === 'light' || res === 'dark' || res === 'system') {
          savedTheme = res;
        }
      } else {
        const local = localStorage.getItem('webstudio_theme');
        if (local === 'light' || local === 'dark' || local === 'system') {
          savedTheme = local as ThemeMode;
        }
      }
    } catch {
      // Keep default dark
    }

    const actual = applyThemeClass(savedTheme);
    set({ theme: savedTheme, resolvedTheme: actual, isInitialized: true });
  },

  setTheme: async (newTheme: ThemeMode) => {
    const actual = applyThemeClass(newTheme);
    set({ theme: newTheme, resolvedTheme: actual });

    try {
      if (window.config?.set) {
        await window.config.set('theme', newTheme);
      } else {
        localStorage.setItem('webstudio_theme', newTheme);
      }
    } catch {
      // Failed to save preference
    }
  },

  toggleTheme: async () => {
    const current = get().resolvedTheme;
    const next: ThemeMode = current === 'dark' ? 'light' : 'dark';
    await get().setTheme(next);
  },
}));
