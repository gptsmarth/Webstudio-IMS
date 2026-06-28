import { useState } from 'react';
import type { StartupStage } from './SplashScreen.types';
import { WebstudioAssetRegistry } from '../registries';

export type { StartupStage } from './SplashScreen.types';

interface SplashScreenProps {
  stage: StartupStage;
  appVersion?: string;
}

const STAGE_PROGRESS: Record<StartupStage, number> = {
  initializing: 18,
  config: 48,
  preparing: 78,
  ready: 100,
};

export function SplashScreen({ stage }: SplashScreenProps): JSX.Element {
  const [logoError, setLogoError] = useState(false);
  const logoLightPath = WebstudioAssetRegistry.getAsset('logoLight');
  const logoPath = WebstudioAssetRegistry.getAsset('logo');
  const progress = STAGE_PROGRESS[stage];

  return (
    <div className="startup-splash">
      <div className="startup-splash__glow" aria-hidden />

      <div className="startup-splash__content">
        <div className="startup-splash__brand">
          <div className="startup-splash__logo-wrap">
            {!logoError ? (
              <img
                src={logoLightPath}
                alt="WEBSTUDIO"
                className="startup-splash__logo"
                onError={(event) => {
                  event.currentTarget.src = logoPath;
                  event.currentTarget.onerror = () => setLogoError(true);
                }}
              />
            ) : (
              <span className="startup-splash__logo-fallback">WEBSTUDIO</span>
            )}
          </div>
          <p className="startup-splash__tagline">Multibrand computer store</p>
          <p className="startup-splash__store">SHUKRANA</p>
        </div>

        <div
          className="startup-splash__progress"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Loading workspace"
        >
          <div className="startup-splash__progress-track">
            <div
              className="startup-splash__progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="startup-splash__stage">Loading workspace…</p>
        </div>
      </div>
    </div>
  );
}
