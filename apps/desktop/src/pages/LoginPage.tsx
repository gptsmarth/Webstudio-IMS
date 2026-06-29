import React, { useState, useEffect, useRef } from 'react';
import { Eye, EyeOff, AlertCircle, CheckCircle2, Server, Clock } from 'lucide-react';
import { AuthenticationService } from '../services/api/AuthenticationService';
import { SetupService } from '../services/api/SetupService';
import { WebstudioAssetRegistry } from '../registries';
import { RecoveryKeyPanel } from '../components/onboarding/RecoveryKeyPanel';
import { sessionFromUser } from '../store/useAuthStore';
import { parseApiError } from '../lib/apiError';
import { isSetupRequired, isSetupRequiredApiError } from '../lib/setupGuard';
import { ASSET_MANIFEST } from '../registries/AssetManifest';
import { useThemeStore, type AuthSession } from '../store';

interface Props {
  companyName: string;
  apiUrl: string;
  appVersion: string;
  onLoginSuccess: (session: AuthSession) => void;
  onSetupRequired: () => void;
}

export const LoginPage: React.FC<Props> = ({ companyName, apiUrl, appVersion, onLoginSuccess, onSetupRequired }) => {
  const { resolvedTheme, toggleTheme } = useThemeStore();
  const [logoError, setLogoError] = useState(false);

  // Login form states
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authStatus, setAuthStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  // Recovery panel states
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryKey, setRecoveryKey] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoverStatus, setRecoverStatus] = useState<string | null>(null);
  const [recoverError, setRecoverError] = useState<string | null>(null);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [recoveryPhase, setRecoveryPhase] = useState<'credentials' | 'new-key'>('credentials');
  const [newRecoveryKey, setNewRecoveryKey] = useState('');
  const [keyConfirmed, setKeyConfirmed] = useState(false);

  const usernameRef = useRef<HTMLInputElement>(null);
  const logoPath = WebstudioAssetRegistry.getAsset('logo');
  const logoLightPath = WebstudioAssetRegistry.getAsset('logoLight');

  // Load saved username
  useEffect(() => {
    try {
      const saved = localStorage.getItem('saved_username');
      if (saved) {
        setUsername(saved);
        setRememberMe(true);
      }
    } catch { /* ignore */ }
    setTimeout(() => usernameRef.current?.focus(), 100);
  }, []);

  // Never show login when the server still requires setup (e.g. after DB reset + hot reload).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const status = await SetupService.getStatus();
        if (!cancelled && isSetupRequired(status)) {
          onSetupRequired();
        }
      } catch {
        // Connection errors are handled by App routing.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onSetupRequired]);

  // Lockout countdown
  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const timer = setInterval(() => {
      setLockoutSeconds((s) => {
        if (s <= 1) {
          clearInterval(timer);
          setError(null);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [lockoutSeconds]);

  // Handle escape to close recovery drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showRecovery) {
        setShowRecovery(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showRecovery]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lockoutSeconds > 0) return;
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }
    setIsSubmitting(true);
    setError(null);

    try {
      const status = await SetupService.getStatus();
      if (isSetupRequired(status)) {
        setIsSubmitting(false);
        onSetupRequired();
        return;
      }

      setAuthStatus('Verifying credentials...');
      const loginResult = await AuthenticationService.login({
        username: username.trim(),
        password,
        remember_me: rememberMe,
        device_label: 'WEBSTUDIO Desktop',
      });
      setAuthStatus('Establishing secure session...');
      let profile = loginResult.user;
      try {
        const me = await AuthenticationService.getCurrentUser();
        profile = { ...me, ...loginResult.user, permissions: me.permissions ?? [] };
      } catch {
        // Fall back to login payload when /me is unavailable
      }
      const session = sessionFromUser(profile);
      await new Promise((resolve) => setTimeout(resolve, 500));

      if (rememberMe) {
        try {
          if (window.storage?.setItem) {
            await window.storage.setItem('saved_username', session.username);
          } else {
            localStorage.setItem('saved_username', session.username);
          }
        } catch { /* ignore */ }
      } else {
        try {
          localStorage.removeItem('saved_username');
        } catch { /* ignore */ }
      }

      setAuthStatus('Authentication successful.');
      setTimeout(() => onLoginSuccess(session), 400);
    } catch (err: unknown) {
      const apiMessage = parseApiError(err, 'Invalid username or password.');
      setIsSubmitting(false);
      setAuthStatus(null);

      if (isSetupRequiredApiError(err)) {
        onSetupRequired();
        return;
      }

      const count = failedAttempts + 1;
      setFailedAttempts(count);
      if (count >= 3) {
        setLockoutSeconds(30);
        setError('Too many failed login attempts. Account access is suspended for 30 seconds.');
      } else {
        setError(apiMessage);
      }
    }
  };

  const closeRecovery = () => {
    setShowRecovery(false);
    setRecoveryPhase('credentials');
    setRecoveryKey('');
    setNewPassword('');
    setConfirmNewPassword('');
    setNewRecoveryKey('');
    setKeyConfirmed(false);
    setRecoverStatus(null);
    setRecoverError(null);
  };

  const handleRecover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recoveryKey.trim() || !newPassword || newPassword !== confirmNewPassword) {
      setRecoverError('Please fill out all fields. Passwords must match.');
      return;
    }
    setIsRecovering(true);
    setRecoverError(null);
    try {
      setRecoverStatus('Validating master key...');
      const result = await SetupService.recoverAdminPassword({
        recovery_key: recoveryKey.trim(),
        new_password: newPassword,
        confirm_password: confirmNewPassword,
      });
      setNewRecoveryKey(result.recovery_key);
      setRecoveryPhase('new-key');
      setKeyConfirmed(false);
      setIsRecovering(false);
      setRecoverStatus(null);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } } };
      setIsRecovering(false);
      setRecoverStatus(null);
      setRecoverError(errorObj.response?.data?.detail ?? 'Invalid recovery key. Please check the code and try again.');
    }
  };

  const handleRecoveryKeyAcknowledged = () => {
    if (!keyConfirmed) return;
    closeRecovery();
    setError('Password reset complete. A new recovery key was generated — store it safely. Sign in with your new password.');
    setFailedAttempts(0);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        backgroundColor: 'var(--color-bg-surface)',
        userSelect: 'none',
        animation: 'fadeIn 200ms ease-out both',
      }}
    >
      {/* ── Left Half: Brand & Multi-Brand Panel ─────────────────── */}
      <div
        style={{
          flex: 1.2,
          background: 'linear-gradient(135deg, #0088CC 0%, #005580 100%)',
          color: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '64px',
          position: 'relative',
        }}
        className="hidden lg:flex"
      >
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40, maxWidth: 460 }}>
          
          {/* Big Webstudio Logo */}
          <div style={{ width: 340, display: 'flex', justifyContent: 'center' }}>
            <img
              src={logoLightPath}
              alt="WEBSTUDIO"
              style={{ width: '100%', height: 'auto', maxHeight: 110, objectFit: 'contain' }}
              onError={(e) => {
                e.currentTarget.src = logoPath;
              }}
            />
          </div>

          {/* Description & Addresses */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <h2 style={{ fontSize: 14, fontWeight: 700, color: 'rgba(255,255,255,0.9)', letterSpacing: '0.08em', textTransform: 'uppercase', margin: 0 }}>
                A Multi-Brand Computer Store
              </h2>
            </div>
            
            <div style={{ width: 32, height: 1.5, backgroundColor: 'rgba(255,255,255,0.3)', margin: '4px auto' }} />
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 4, textAlign: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.5)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Outlet 1</span>
                <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.4 }}>22, D.A.V. Market, Opp. Madhu Hotel, Yamunanagar</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.5)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Outlet 2</span>
                <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.4 }}>26-29 F, D.A.V. Market, Yamunanagar</span>
              </div>
            </div>
          </div>

          {/* Multibrand Logos Grid */}
          <div style={{ width: '100%', marginTop: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.5)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 20 }}>
              Official Brands
            </p>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '24px 16px',
                alignItems: 'center',
                justifyItems: 'center',
              }}
            >
              {[
                { name: 'apple', src: ASSET_MANIFEST.brandLogos.apple },
                { name: 'dell', src: ASSET_MANIFEST.brandLogos.dell },
                { name: 'hp', src: ASSET_MANIFEST.brandLogos.hp },
                { name: 'lenovo', src: ASSET_MANIFEST.brandLogos.lenovo },
                { name: 'sandisk', src: ASSET_MANIFEST.brandLogos.sandisk },
                { name: 'asus', src: ASSET_MANIFEST.brandLogos.asus },
                { name: 'logitech', src: ASSET_MANIFEST.brandLogos.logitech },
                { name: 'canon', src: ASSET_MANIFEST.brandLogos.canon },
              ].map((brand) => (
                <div
                  key={brand.name}
                  style={{
                    height: 24,
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <img
                    src={brand.src}
                    alt={brand.name}
                    style={{
                      maxHeight: '100%',
                      maxWidth: '100%',
                      objectFit: 'contain',
                      filter: 'brightness(0) invert(1)',
                      opacity: 0.65,
                      transition: 'opacity 0.2s ease',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.65'; }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Info */}
        <div style={{ position: 'absolute', bottom: 40, left: 40, right: 40, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)' }}>
          <span>WEBSTUDIO IMS v{appVersion}</span>
          <span>SECURE CONNECTION ACTIVE</span>
        </div>
      </div>

      {/* ── Right Half: Login Panel ─────────────────────────────── */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px 32px',
        }}
      >
        <div style={{ width: '100%', maxWidth: 400 }}>
          {/* Header */}
          <div style={{ marginBottom: 32 }}>
            {/* Show logo on small screens only */}
            <div className="lg:hidden" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-bg-raised)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 6,
                }}
              >
                {!logoError ? (
                  <img src={logoPath} alt="WS" style={{ width: '100%', height: '100%', objectFit: 'contain' }} onError={() => setLogoError(true)} />
                ) : (
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-primary-600)' }}>WS</span>
                )}
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>WEBSTUDIO IMS</span>
            </div>

            <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: '-0.02em', marginBottom: 8 }}>
              Sign in
            </h2>
            <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', margin: 0 }}>
              Access the {companyName || 'WEBSTUDIO'} workspace
            </p>
          </div>

          {/* Messages */}
          {lockoutSeconds > 0 && (
            <div className="alert alert-warning" style={{ marginBottom: 20, animation: 'fadeIn 150ms ease-out both' }}>
              <Clock size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                Too many failed attempts. Suspended for <strong>{lockoutSeconds}s</strong>.
              </span>
            </div>
          )}

          {error && lockoutSeconds === 0 && (
            <div className="alert alert-danger" style={{ marginBottom: 20, animation: 'fadeIn 150ms ease-out both' }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{error}</span>
            </div>
          )}

          {authStatus && (
            <div className="alert alert-info" style={{ marginBottom: 20, animation: 'fadeIn 150ms ease-out both' }}>
              <span style={{ width: 12, height: 12, border: '1.5px solid var(--color-primary-200)', borderTopColor: 'var(--color-primary-500)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', display: 'inline-block', flexShrink: 0 }} />
              <span>{authStatus}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={(e) => void handleLogin(e)} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              <label htmlFor="login-username" className="form-label">Username</label>
              <input
                ref={usernameRef}
                id="login-username"
                type="text"
                className="input"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isSubmitting || lockoutSeconds > 0}
                autoComplete="username"
                required
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              <label htmlFor="login-password" className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="input"
                  style={{ paddingRight: 36 }}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting || lockoutSeconds > 0}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  style={{
                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                    color: 'var(--color-text-tertiary)', display: 'flex', alignItems: 'center',
                  }}
                  onClick={() => setShowPassword((p) => !p)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  style={{ accentColor: 'var(--color-primary-500)' }}
                />
                <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Remember username</span>
              </label>

              <button
                type="button"
                onClick={() => { setShowRecovery(true); setError(null); }}
                style={{
                  fontSize: 12,
                  color: 'var(--color-primary-600)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  fontFamily: 'inherit',
                  fontWeight: 500,
                }}
              >
                Recover Access
              </button>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || lockoutSeconds > 0}
              style={{ width: '100%', marginTop: 8, height: 40 }}
            >
              {isSubmitting ? (
                <>
                  <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite', display: 'inline-block', flexShrink: 0 }} />
                  <span>Signing in...</span>
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Connection Info */}
          <div
            style={{
              marginTop: 32,
              padding: '12px 16px',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-bg-raised)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
              <Server size={12} style={{ color: 'var(--color-text-tertiary)', flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 }} title={apiUrl}>
                {apiUrl}
              </span>
            </div>
            <span className="badge badge-success" style={{ fontSize: 10, padding: '2px 6px', flexShrink: 0 }}>Connected</span>
          </div>

          {/* Footer Controls */}
          <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: 'var(--color-text-disabled)' }}>
            <span>v{appVersion}</span>
            <button
              onClick={() => void toggleTheme()}
              style={{ color: 'var(--color-primary-600)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'inherit', fontWeight: 500 }}
            >
              {resolvedTheme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Slide-over Recovery Panel ─────────────────────────────────── */}
      {showRecovery && (
        <>
          {/* Backdrop */}
          <div
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0,0,0,0.35)',
              backdropFilter: 'blur(4px)',
              zIndex: 40,
              animation: 'fadeIn 150ms ease-out both',
            }}
            onClick={() => {
              if (recoveryPhase === 'new-key') return;
              closeRecovery();
            }}
          />

          {/* Panel */}
          <div
            className={`recovery-panel ${recoveryPhase === 'new-key' ? 'recovery-panel--wide' : ''}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="recovery-panel-title"
          >
            {/* Header */}
            <div className="recovery-panel__header">
              <div>
                <h2 id="recovery-panel-title" className="recovery-panel__title">
                  {recoveryPhase === 'new-key' ? 'New Recovery Key' : 'Recover Access'}
                </h2>
                <p className="recovery-panel__subtitle">
                  {recoveryPhase === 'new-key'
                    ? 'Your password was reset. Save this new key before continuing.'
                    : 'Reset credentials using your recovery key'}
                </p>
              </div>
              <button
                onClick={() => {
                  if (recoveryPhase === 'new-key' && !keyConfirmed) return;
                  closeRecovery();
                }}
                className="btn btn-ghost btn-sm recovery-panel__close"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            {/* Body */}
            <div className="recovery-panel__body">
              {recoveryPhase === 'credentials' ? (
              <form onSubmit={(e) => void handleRecover(e)} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="alert alert-info">
                  <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>Enter the 24-character master key to authenticate and update your password.</span>
                </div>

                {recoverError && (
                  <div className="alert alert-danger" style={{ animation: 'fadeIn 150ms ease-out both' }}>
                    <AlertCircle size={14} style={{ flexShrink: 0 }} />
                    <span>{recoverError}</span>
                  </div>
                )}

                {recoverStatus && (
                  <div className="alert alert-success" style={{ animation: 'fadeIn 150ms ease-out both' }}>
                    <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
                    <span>{recoverStatus}</span>
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                  <label htmlFor="recovery-key" className="form-label">Recovery Key</label>
                  <input
                    id="recovery-key"
                    type="text"
                    className="input"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 12, letterSpacing: '0.04em' }}
                    placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                    value={recoveryKey}
                    onChange={(e) => setRecoveryKey(e.target.value)}
                    autoFocus
                    disabled={isRecovering}
                    spellCheck={false}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                  <label htmlFor="new-password" className="form-label">New Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      id="new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      className="input"
                      style={{ paddingRight: 36 }}
                      placeholder="Min. 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      disabled={isRecovering}
                      required
                    />
                    <button
                      type="button"
                      style={{
                        position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                        background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                        color: 'var(--color-text-tertiary)', display: 'flex', alignItems: 'center',
                      }}
                      onClick={() => setShowNewPassword((p) => !p)}
                      tabIndex={-1}
                    >
                      {showNewPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                  <label htmlFor="confirm-new-password" className="form-label">Confirm Password</label>
                  <input
                    id="confirm-new-password"
                    type="password"
                    className={`input ${newPassword && confirmNewPassword && newPassword !== confirmNewPassword ? 'input-error' : ''}`}
                    placeholder="Repeat new password"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    disabled={isRecovering}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isRecovering || !recoveryKey.trim() || !newPassword || newPassword !== confirmNewPassword}
                  style={{ width: '100%', height: 40 }}
                >
                  {isRecovering ? (
                    <>
                      <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.7s linear infinite', display: 'inline-block', flexShrink: 0 }} />
                      <span>Verifying key...</span>
                    </>
                  ) : (
                    'Reset Password'
                  )}
                </button>
              </form>
              ) : (
                <div className="recovery-panel__new-key">
                  <div className="alert alert-success">
                    <CheckCircle2 size={14} aria-hidden="true" />
                    <span>Password updated successfully.</span>
                  </div>

                  <RecoveryKeyPanel
                    recoveryKey={newRecoveryKey}
                    title="Replacement Recovery Key"
                    description="A new recovery key was generated automatically. The previous key no longer works. Store this key before closing this panel."
                    confirmLabel="I have saved the new recovery key in a secure location."
                    hasConfirmed={keyConfirmed}
                    onConfirmChange={setKeyConfirmed}
                  />

                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ width: '100%', height: 40 }}
                    disabled={!keyConfirmed}
                    onClick={handleRecoveryKeyAcknowledged}
                  >
                    Continue to Sign In
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
