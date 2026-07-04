import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { WebstudioAssetRegistry } from '../../registries/WebstudioAssetRegistry';
import type { WebstudioAssetKey } from '../../registries/AssetManifest';
import { assetUrlsEquivalent } from '../../utils/resolvePublicAsset';
import { useThemeStore } from '../../store';

/**
 * Logo ink variants for UI surfaces.
 * - onDarkPanel: login/setup left panel (light lettering on brand gradient)
 * - light: light app surfaces (dark lettering)
 * - dark: dark app surfaces (light lettering)
 * - auto: follow current theme
 */
export type WebstudioLogoVariant = 'auto' | 'onDarkPanel' | 'light' | 'dark';

interface WebstudioLogoImageProps {
  variant?: WebstudioLogoVariant;
  className?: string;
  style?: CSSProperties;
  alt?: string;
  fallbackText?: string;
}

function candidateKeys(
  variant: WebstudioLogoVariant,
  theme: 'light' | 'dark',
): WebstudioAssetKey[] {
  switch (variant) {
    case 'onDarkPanel':
      return ['logoLight', 'logoDark', 'logo'];
    case 'light':
      return ['logoDark', 'logo', 'logoLight'];
    case 'dark':
      return ['logoLight', 'logo', 'logoDark'];
    case 'auto':
    default:
      return theme === 'dark'
        ? ['logoLight', 'logoDark', 'logo']
        : ['logoDark', 'logoLight', 'logo'];
  }
}

export function WebstudioLogoImage({
  variant = 'auto',
  className,
  style,
  alt = 'WEBSTUDIO',
  fallbackText = 'WEBSTUDIO',
}: WebstudioLogoImageProps): JSX.Element {
  const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
  const keys = useMemo(() => candidateKeys(variant, resolvedTheme), [variant, resolvedTheme]);
  const sources = useMemo(() => keys.map((key) => WebstudioAssetRegistry.getAsset(key)), [keys]);
  const [sourceIndex, setSourceIndex] = useState(0);
  const [showFallback, setShowFallback] = useState(false);

  useEffect(() => {
    setSourceIndex(0);
    setShowFallback(false);
  }, [sources.join('|')]);

  if (showFallback) {
    return (
      <span className={className} style={style} aria-label={alt}>
        {fallbackText}
      </span>
    );
  }

  const src = sources[sourceIndex] ?? sources[0];

  return (
    <img
      key={src}
      src={src}
      alt={alt}
      className={className}
      style={style}
      onError={(event) => {
        const img = event.currentTarget;
        const nextIndex = sourceIndex + 1;
        if (nextIndex < sources.length && !assetUrlsEquivalent(img.src, sources[nextIndex])) {
          setSourceIndex(nextIndex);
          return;
        }
        setShowFallback(true);
      }}
    />
  );
}
