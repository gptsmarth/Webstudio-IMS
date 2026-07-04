export const ASSET_MANIFEST = {
  brandLogos: {
    asus: '/assets/brand-logos/asus.svg',
    acer: '/assets/brand-logos/acer.svg',
    hp: '/assets/brand-logos/hp.svg',
    dell: '/assets/brand-logos/dell.svg',
    lenovo: '/assets/brand-logos/lenovo.svg',
    msi: '/assets/brand-logos/msi.svg',
    apple: '/assets/brand-logos/apple.svg',
    sandisk: '/assets/brand-logos/sandisk.svg',
    logitech: '/assets/brand-logos/logitech.svg',
    'tp-link': '/assets/brand-logos/tp-link.svg',
    canon: '/assets/brand-logos/canon.svg',
    epson: '/assets/brand-logos/epson.svg',
    brother: '/assets/brand-logos/brother.svg',
    default: '/assets/brand-logos/default.svg',
  },
  brandLogosPng: {
    asus: '/assets/brand-logos/asus.png',
    acer: '/assets/brand-logos/acer.png',
    hp: '/assets/brand-logos/hp.png',
    dell: '/assets/brand-logos/dell.png',
    lenovo: '/assets/brand-logos/lenovo.png',
    msi: '/assets/brand-logos/msi.png',
    apple: '/assets/brand-logos/apple.png',
    sandisk: '/assets/brand-logos/sandisk.png',
    logitech: '/assets/brand-logos/logitech.png',
    'tp-link': '/assets/brand-logos/tp-link.png',
    canon: '/assets/brand-logos/canon.png',
    epson: '/assets/brand-logos/epson.png',
    brother: '/assets/brand-logos/brother.png',
    default: '/assets/brand-logos/default.png',
  },
  webstudio: {
    logo: '/assets/webstudio/logo.svg',
    logoDark: '/assets/webstudio/logo-dark.svg',
    logoLight: '/assets/webstudio/logo-light.svg',
    icon: '/assets/webstudio/icon.svg',
    iconIco: '/assets/webstudio/icon.ico',
    iconIcns: '/assets/webstudio/icon.icns',
    iconPng: '/assets/webstudio/icon.png',
    splash: '/assets/webstudio/splash.svg',
    favicon: '/assets/webstudio/favicon.svg',
  },
  placeholders: {
    laptop: '/assets/placeholders/laptop-default.svg',
    desktop: '/assets/placeholders/desktop-default.svg',
    accessory: '/assets/placeholders/accessory-default.svg',
    generic: '/assets/placeholders/generic-default.svg',
  },
  illustrations: {
    'empty-inventory': '/assets/illustrations/empty-inventory.svg',
    error: '/assets/illustrations/error.svg',
    success: '/assets/illustrations/success.svg',
    offline: '/assets/illustrations/offline.svg',
    onboarding: '/assets/illustrations/onboarding.svg',
  },
  icons: {
    search: '/assets/icons/search.svg',
    filter: '/assets/icons/filter.svg',
    add: '/assets/icons/add.svg',
    refresh: '/assets/icons/refresh.svg',
    close: '/assets/icons/close.svg',
    sync: '/assets/icons/sync.svg',
    warning: '/assets/icons/warning.svg',
    check: '/assets/icons/check.svg',
  },
} as const;

export type BrandLogoKey = keyof typeof ASSET_MANIFEST.brandLogos;
export type BundledBrandLogoKey = Exclude<BrandLogoKey, 'default'>;

/** All bundled brand logos (catalogue picker, inventory) — excludes default. */
export const BUNDLED_BRAND_LOGO_KEYS = (
  Object.keys(ASSET_MANIFEST.brandLogos) as BrandLogoKey[]
).filter((key): key is BundledBrandLogoKey => key !== 'default');

/**
 * Login / setup wizard left panel — SHUKRANA official brands only (display order).
 * Bundled in desktop .exe and .dmg via the same AssetManifest + public/assets/brand-logos/.
 */
/** Login / setup left panel — SHUKRANA official brands (display order, 4×2 grid). */
export const OFFICIAL_SHOWCASE_BRANDS = [
  'apple',
  'dell',
  'hp',
  'lenovo',
  'sandisk',
  'asus',
  'logitech',
  'canon',
] as const satisfies readonly BundledBrandLogoKey[];
export type WebstudioAssetKey = keyof typeof ASSET_MANIFEST.webstudio;
export type PlaceholderAssetKey = keyof typeof ASSET_MANIFEST.placeholders;
export type IllustrationAssetKey = keyof typeof ASSET_MANIFEST.illustrations;
export type IconAssetKey = keyof typeof ASSET_MANIFEST.icons;
