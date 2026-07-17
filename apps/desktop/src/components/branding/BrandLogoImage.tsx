import { type CSSProperties, useEffect, useState } from 'react';
import { brandLogoSrc } from '../../lib/catalogue';
import { BrandLogoRegistry } from '../../registries/BrandLogoRegistry';
import { OFFICIAL_SHOWCASE_BRANDS } from '../../registries/AssetManifest';
import { assetUrlsEquivalent } from '../../utils/resolvePublicAsset';
import { BrandLogoService } from '../../services/images/BrandLogoService';

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
  const isUploaded = BrandLogoRegistry.isUploadedLogo(logoFilename);
  const [uploadedSrc, setUploadedSrc] = useState<string | null>(() =>
    isUploaded && logoFilename ? BrandLogoService.getCached(logoFilename) : null,
  );

  useEffect(() => {
    if (!isUploaded || !logoFilename) {
      setUploadedSrc(null);
      return;
    }
    const cached = BrandLogoService.getCached(logoFilename);
    if (cached) {
      setUploadedSrc(cached);
      return;
    }
    let active = true;
    void BrandLogoService.resolve(logoFilename).then((src) => {
      if (active) setUploadedSrc(src);
    });
    return () => {
      active = false;
    };
  }, [isUploaded, logoFilename]);

  // Uploaded logo resolved via the proxy — render it; otherwise fall back to
  // the bundled/name-matched logo below while it loads or if it fails.
  const primarySrc = isUploaded && uploadedSrc ? uploadedSrc : brandLogoSrc(brand, logoFilename);

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
        if (stage === 'png' && !assetUrlsEquivalent(img.src, defaultLogo)) {
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
