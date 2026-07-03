import { ArrowLeft } from 'lucide-react';

interface PageBackButtonProps {
  label?: string;
  onClick: () => void;
  disabled?: boolean;
}

export function PageBackButton({
  label = 'Back',
  onClick,
  disabled,
}: PageBackButtonProps): JSX.Element {
  return (
    <button
      type="button"
      className="page-back-btn"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
    >
      <ArrowLeft size={16} aria-hidden />
      <span>{label}</span>
    </button>
  );
}
