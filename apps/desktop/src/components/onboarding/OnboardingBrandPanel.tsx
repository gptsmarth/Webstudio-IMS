import { ASSET_MANIFEST } from '../../registries/AssetManifest';
import { WebstudioAssetRegistry } from '../../registries';

interface OnboardingBrandPanelProps {
  appVersion: string;
  footerRight?: string;
}

const BRAND_LOGOS = [
  { name: 'apple', src: ASSET_MANIFEST.brandLogos.apple },
  { name: 'dell', src: ASSET_MANIFEST.brandLogos.dell },
  { name: 'hp', src: ASSET_MANIFEST.brandLogos.hp },
  { name: 'lenovo', src: ASSET_MANIFEST.brandLogos.lenovo },
  { name: 'asus', src: ASSET_MANIFEST.brandLogos.asus },
  { name: 'sandisk', src: ASSET_MANIFEST.brandLogos.sandisk },
  { name: 'logitech', src: ASSET_MANIFEST.brandLogos.logitech },
  { name: 'canon', src: ASSET_MANIFEST.brandLogos.canon },
] as const;

export function OnboardingBrandPanel({
  appVersion,
  footerRight = 'SECURE CONNECTION ACTIVE',
}: OnboardingBrandPanelProps): JSX.Element {
  const logoLightPath = WebstudioAssetRegistry.getAsset('logoLight');
  const logoPath = WebstudioAssetRegistry.getAsset('logo');

  return (
    <aside className="onboarding-brand-panel" aria-hidden="true">
      <div className="onboarding-brand-panel__content">
        <div className="onboarding-brand-panel__logo-wrap">
          <img
            src={logoLightPath}
            alt="WEBSTUDIO"
            className="onboarding-brand-panel__logo"
            onError={(e) => {
              e.currentTarget.src = logoPath;
            }}
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
            {BRAND_LOGOS.map((brand) => (
              <div key={brand.name} className="onboarding-brand-panel__brand-cell">
                <img
                  src={brand.src}
                  alt={brand.name}
                  className="onboarding-brand-panel__brand-logo"
                />
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
