import { useState } from 'react';
import { WebstudioAssetRegistry } from '../../registries';

interface StartupBrandPanelProps {
  appVersion?: string;
  footerLeft?: string;
  footerRight?: string;
  compact?: boolean;
}

export function StartupBrandPanel({
  appVersion,
  footerLeft = 'WEBSTUDIO IMS',
  footerRight,
  compact = false,
}: StartupBrandPanelProps): JSX.Element {
  const [logoError, setLogoError] = useState(false);
  const logoLightPath = WebstudioAssetRegistry.getAsset('logoLight');
  const logoPath = WebstudioAssetRegistry.getAsset('logo');

  return (
    <div className={`startup-brand ${compact ? 'startup-brand--compact' : ''}`}>
      <div className="startup-brand__content">
        <div className="startup-brand__logo-wrap">
          {!logoError ? (
            <img
              src={logoLightPath}
              alt="WEBSTUDIO"
              className="startup-brand__logo"
              onError={(e) => {
                e.currentTarget.src = logoPath;
                e.currentTarget.onerror = () => setLogoError(true);
              }}
            />
          ) : (
            <span className="startup-brand__logo-fallback">WEBSTUDIO</span>
          )}
        </div>

        <div className="startup-brand__intro">
          <p className="startup-brand__product">Inventory Management System</p>
          <div className="startup-brand__divider" aria-hidden />
          <p className="startup-brand__tagline">
            Serial-tracked inventory, sales, and operations for multi-location retail.
          </p>
        </div>
      </div>

      {(footerLeft || footerRight || appVersion) && (
        <div className="startup-brand__footer">
          <span>{footerLeft}{appVersion ? ` v${appVersion}` : ''}</span>
          {footerRight && <span>{footerRight}</span>}
        </div>
      )}
    </div>
  );
}
