import type { ReactNode } from 'react';

export function Section({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <section className="stg-section">
      <h2 className="stg-section__title">{title}</h2>
      <div className="stg-section__body">{children}</div>
    </section>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}): JSX.Element {
  return (
    <label className="stg-field">
      <span className="stg-field__label">{label}</span>
      {children}
      {hint && <span className="stg-field__hint">{hint}</span>}
    </label>
  );
}

export function Readonly({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="stg-readonly">
      <span className="stg-readonly__label">{label}</span>
      <span className="stg-readonly__value">{value}</span>
    </div>
  );
}

export function SaveButton({
  label,
  saving,
  canWrite,
}: {
  label: string;
  saving: boolean;
  canWrite: boolean;
}): JSX.Element | null {
  if (!canWrite) return null;
  return (
    <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
      {label}
    </button>
  );
}
