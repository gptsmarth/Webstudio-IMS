import type { CSSProperties } from 'react';
import { brandLogoSrc } from '../../lib/catalogue';
import { BrandLogoRegistry } from '../../registries/BrandLogoRegistry';
import { OFFICIAL_SHOWCASE_BRANDS } from '../../registries/AssetManifest';

interface BrandLogoImageProps {
  brand: string;
  logoFilename?: string | null;
  className?: string;
  alt?: string;
  style?: CSSProperties;
  loading?: 'lazy' | 'eager';
}

export function BrandLogoImage({
  brand,
  logoFilename,
  className,
  alt = '',
  style,
  loading = 'lazy',
}: BrandLogoImageProps): JSX.Element {
  const primarySrc = brandLogoSrc(brand, logoFilename);

  return (
    <img
      src={primarySrc}
      alt={alt}
      className={className}
      style={style}
      loading={loading}
      onError={(event) => {
        const img = event.currentTarget;
        const stage = img.dataset.fallbackStage ?? 'primary';
        const defaultLogo = BrandLogoRegistry.getLogo('default');

        if (stage === 'primary') {
          img.dataset.fallbackStage = 'png';
          img.src = BrandLogoRegistry.getFallbackLogo(brand);
          return;
        }
        if (stage === 'png' && img.src !== defaultLogo) {
          img.dataset.fallbackStage = 'default';
          img.src = defaultLogo;
          return;
        }
        img.onerror = null;
      }}
    />
  );
}

export { OFFICIAL_SHOWCASE_BRANDS };
