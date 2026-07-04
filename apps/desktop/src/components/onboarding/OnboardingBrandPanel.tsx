import { WebstudioLogoImage } from '../branding/WebstudioLogoImage';
import { BrandLogoImage, OFFICIAL_SHOWCASE_BRANDS } from '../branding/BrandLogoImage';

interface OnboardingBrandPanelProps {
  appVersion: string;
  footerRight?: string;
}

export function OnboardingBrandPanel({
  appVersion,
  footerRight = 'SECURE CONNECTION ACTIVE',
}: OnboardingBrandPanelProps): JSX.Element {
  return (
    <aside className="onboarding-brand-panel" aria-hidden="true">
      <div className="onboarding-brand-panel__content">
        <div className="onboarding-brand-panel__logo-wrap">
          <WebstudioLogoImage
            variant="onDarkPanel"
            alt="WEBSTUDIO"
            className="onboarding-brand-panel__logo"
          />
        </div>

        <div className="onboarding-brand-panel__intro">
          <h2 className="onboarding-brand-panel__tagline">A Multi-Brand Computer Store</h2>
          <div className="onboarding-brand-panel__divider" />
          <div className="onboarding-brand-panel__addresses">
            <div>
              <span className="onboarding-brand-panel__outlet-label">Outlet 1</span>
              <span className="onboarding-brand-panel__outlet-text">
                22, D.A.V. Market, Opp. Madhu Hotel, Yamunanagar
              </span>
            </div>
            <div>
              <span className="onboarding-brand-panel__outlet-label">Outlet 2</span>
              <span className="onboarding-brand-panel__outlet-text">
                26-29 F, D.A.V. Market, Yamunanagar
              </span>
            </div>
          </div>
        </div>

        <div className="onboarding-brand-panel__brands">
          <p className="onboarding-brand-panel__brands-label">Official Brands</p>
          <div className="onboarding-brand-panel__brands-grid">
            {OFFICIAL_SHOWCASE_BRANDS.map((name) => (
              <div key={name} className="onboarding-brand-panel__brand-cell">
                <BrandLogoImage brand={name} className="onboarding-brand-panel__brand-logo" />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="onboarding-brand-panel__footer">
        <span>WEBSTUDIO IMS v{appVersion}</span>
        <span>{footerRight}</span>
      </div>
    </aside>
  );
}
