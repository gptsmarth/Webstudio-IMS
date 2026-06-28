export type TableDensity = 'comfortable' | 'compact';
export type SidebarBehaviour = 'expanded' | 'collapsed';

export interface AppearancePreferences {
  compactMode: boolean;
  tableDensity: TableDensity;
  sidebarBehaviour: SidebarBehaviour;
}

const STORAGE_KEY = 'webstudio_appearance_prefs';

const DEFAULTS: AppearancePreferences = {
  compactMode: false,
  tableDensity: 'comfortable',
  sidebarBehaviour: 'expanded',
};

export function loadAppearancePreferences(): AppearancePreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<AppearancePreferences>;
    return {
      compactMode: parsed.compactMode ?? DEFAULTS.compactMode,
      tableDensity: parsed.tableDensity ?? DEFAULTS.tableDensity,
      sidebarBehaviour: parsed.sidebarBehaviour ?? DEFAULTS.sidebarBehaviour,
    };
  } catch {
    return DEFAULTS;
  }
}

export function saveAppearancePreferences(prefs: AppearancePreferences): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  document.body.classList.toggle('stg-compact', prefs.compactMode);
  document.body.dataset.tableDensity = prefs.tableDensity;
  document.body.dataset.sidebarBehaviour = prefs.sidebarBehaviour;
}

export function initAppearancePreferences(): void {
  saveAppearancePreferences(loadAppearancePreferences());
}
