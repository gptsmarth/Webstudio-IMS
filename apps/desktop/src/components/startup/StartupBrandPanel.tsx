import { WebstudioLogoImage } from '../branding/WebstudioLogoImage';

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
  return (
    <div className={`startup-brand ${compact ? 'startup-brand--compact' : ''}`}>
      <div className="startup-brand__content">
        <div className="startup-brand__logo-wrap">
          <WebstudioLogoImage
            variant="onDarkPanel"
            alt="WEBSTUDIO"
            className="startup-brand__logo"
          />
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
          <span>
            {footerLeft}
            {appVersion ? ` v${appVersion}` : ''}
          </span>
          {footerRight && <span>{footerRight}</span>}
        </div>
      )}
    </div>
  );
}
