import { useState } from 'react';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import { SetupService } from '../services/api/SetupService';
import { OnboardingBrandPanel } from '../components/onboarding/OnboardingBrandPanel';
import { WebstudioLogoImage } from '../components/branding/WebstudioLogoImage';
import { RecoveryKeyPanel } from '../components/onboarding/RecoveryKeyPanel';
import { SetupStepper } from '../components/onboarding/SetupStepper';

interface Props {
  onSetupComplete: () => void;
  initialRecoveryKey?: string | null;
  isDemoMode?: boolean;
  appVersion: string;
}

const STEPS = [
  { number: 1, label: 'Organization' },
  { number: 2, label: 'Administrator' },
  { number: 3, label: 'Recovery Key' },
];

export function SetupWizardPage({
  onSetupComplete,
  initialRecoveryKey,
  isDemoMode,
  appVersion,
}: Props): JSX.Element {
  const [step, setStep] = useState<1 | 2 | 3>(initialRecoveryKey ? 3 : 1);
  const [isOfflineDemo, setIsOfflineDemo] = useState(Boolean(isDemoMode));

  const [companyName, setCompanyName] = useState('');
  const [mainAdminName, setMainAdminName] = useState('');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [recoveryKey, setRecoveryKey] = useState(initialRecoveryKey ?? '');
  const [hasConfirmed, setHasConfirmed] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDemo = isOfflineDemo || recoveryKey === 'DEMO-PREVIEW-MODE-BACKEND-UNAVAILABLE';

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setError('Please enter your organization name.');
      return;
    }
    setError(null);
    setStep(2);
  };

  const handleStep2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mainAdminName.trim()) {
      setError('Please enter the administrator full name.');
      return;
    }
    if (!username.trim()) {
      setError('Please enter a username.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (isOfflineDemo) throw new Error('Offline Demo Mode');
      const res = await SetupService.initialize({
        company_name: companyName.trim(),
        main_admin_name: mainAdminName.trim(),
        username: username.trim(),
        password,
        confirm_password: confirmPassword,
      });
      setRecoveryKey(res.recovery_key ?? '');
      setStep(3);
    } catch (err: unknown) {
      const errorObj = err as { response?: { status?: number; data?: { detail?: string } } };
      const isOffline =
        !errorObj.response || (errorObj.response.status ?? 0) >= 500 || isOfflineDemo;
      if (isOffline) {
        setIsOfflineDemo(true);
        setRecoveryKey('DEMO-PREVIEW-MODE-BACKEND-UNAVAILABLE');
        setStep(3);
      } else {
        setError(
          errorObj.response?.data?.detail ??
            'Setup failed. Please check your details and try again.',
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCompleteSetup = async () => {
    if (!hasConfirmed) return;
    setIsSubmitting(true);
    setError(null);
    try {
      if (!isDemo) {
        await SetupService.confirmRecoveryKey();
      }
      onSetupComplete();
    } catch (err: unknown) {
      const errorObj = err as { response?: { status?: number; data?: { detail?: string } } };
      const isOffline =
        !errorObj.response || (errorObj.response.status ?? 0) >= 500 || isOfflineDemo;
      if (isOffline) {
        onSetupComplete();
      } else {
        setError(errorObj.response?.data?.detail ?? 'Could not confirm setup. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="onboarding-layout">
      <OnboardingBrandPanel appVersion={appVersion} footerRight="FIRST-TIME SETUP" />

      <main className="onboarding-main setup-wizard">
        <div className="onboarding-main__inner setup-wizard__inner">
          <header className="setup-wizard__header">
            <div className="setup-wizard__mobile-logo lg:hidden">
              <div className="setup-wizard__mobile-logo-box">
                <WebstudioLogoImage variant="light" alt="WEBSTUDIO" fallbackText="WS" />
              </div>
              <span>WEBSTUDIO IMS</span>
            </div>

            <h1 className="setup-wizard__title">System Setup</h1>
            <p className="setup-wizard__subtitle">
              Configure your organization and administrator account.
            </p>
          </header>

          <SetupStepper steps={STEPS} currentStep={step} />

          {isDemo && (
            <div className="alert alert-warning setup-wizard__alert">
              <AlertCircle size={14} aria-hidden="true" />
              <span>UI Preview Mode — backend unavailable. Data is not persisted.</span>
            </div>
          )}

          {error && (
            <div className="alert alert-danger setup-wizard__alert">
              <AlertCircle size={14} aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {step === 1 && (
            <form onSubmit={handleStep1Submit} className="setup-wizard__form animate-fade-in">
              <div className="setup-wizard__section">
                <h2 className="setup-wizard__section-title">Organization Profile</h2>
                <p className="setup-wizard__section-text">
                  This name appears on reports, receipts, and throughout the system.
                </p>
              </div>

              <div className="setup-wizard__field">
                <label htmlFor="company-name" className="form-label">
                  Organization Name
                </label>
                <input
                  id="company-name"
                  type="text"
                  className="input"
                  placeholder="e.g. WEBSTUDIO"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              <div className="setup-wizard__actions setup-wizard__actions--end">
                <button type="submit" className="btn btn-primary">
                  Continue
                </button>
              </div>
            </form>
          )}

          {step === 2 && (
            <form
              onSubmit={(e) => void handleStep2Submit(e)}
              className="setup-wizard__form animate-fade-in"
            >
              <div className="setup-wizard__section">
                <h2 className="setup-wizard__section-title">Administrator Account</h2>
                <p className="setup-wizard__section-text">
                  Create the main administrator account. Additional users can be added after setup.
                </p>
              </div>

              <div className="setup-wizard__field">
                <label htmlFor="admin-name" className="form-label">
                  Full Name
                </label>
                <input
                  id="admin-name"
                  type="text"
                  className="input"
                  placeholder="e.g. Rahul Sharma"
                  value={mainAdminName}
                  onChange={(e) => setMainAdminName(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              <div className="setup-wizard__field">
                <label htmlFor="username" className="form-label">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  className="input"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className="setup-wizard__field-row">
                <div className="setup-wizard__field">
                  <label htmlFor="password" className="form-label">
                    Password
                  </label>
                  <div className="setup-wizard__input-wrap">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      className="input setup-wizard__input-with-icon"
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="setup-wizard__eye-btn"
                      onClick={() => setShowPassword((p) => !p)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <div className="setup-wizard__field">
                  <label htmlFor="confirm-password" className="form-label">
                    Confirm Password
                  </label>
                  <div className="setup-wizard__input-wrap">
                    <input
                      id="confirm-password"
                      type={showConfirm ? 'text' : 'password'}
                      className={`input setup-wizard__input-with-icon ${password && confirmPassword && password !== confirmPassword ? 'input-error' : ''}`}
                      placeholder="Repeat password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="setup-wizard__eye-btn"
                      onClick={() => setShowConfirm((p) => !p)}
                      aria-label={showConfirm ? 'Hide password' : 'Show password'}
                    >
                      {showConfirm ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="setup-wizard__actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setStep(1);
                    setError(null);
                  }}
                >
                  Back
                </button>
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <span className="setup-wizard__spinner" aria-hidden="true" />
                      <span>Setting up…</span>
                    </>
                  ) : (
                    'Generate Recovery Key'
                  )}
                </button>
              </div>
            </form>
          )}

          {step === 3 && (
            <div className="setup-wizard__form animate-fade-in">
              <RecoveryKeyPanel
                recoveryKey={recoveryKey}
                isDemo={isDemo}
                hasConfirmed={hasConfirmed}
                onConfirmChange={setHasConfirmed}
              />

              <div className="setup-wizard__actions setup-wizard__actions--end">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!hasConfirmed || isSubmitting}
                  onClick={() => void handleCompleteSetup()}
                >
                  {isSubmitting ? (
                    <>
                      <span className="setup-wizard__spinner" aria-hidden="true" />
                      <span>Completing setup…</span>
                    </>
                  ) : (
                    'Complete Setup'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
