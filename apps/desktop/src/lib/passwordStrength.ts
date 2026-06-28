export type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong';

export interface PasswordStrengthResult {
  score: PasswordStrength;
  label: string;
  percent: number;
  meetsMinimum: boolean;
  hints: string[];
}

const MIN_LENGTH = 10;

export function assessPasswordStrength(password: string): PasswordStrengthResult {
  const hints: string[] = [];
  let points = 0;

  if (password.length >= MIN_LENGTH) points += 1;
  else hints.push(`At least ${MIN_LENGTH} characters`);

  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) points += 1;
  else hints.push('Mix upper and lower case');

  if (/\d/.test(password)) points += 1;
  else hints.push('Include a number');

  if (/[^A-Za-z0-9]/.test(password)) points += 1;

  const meetsMinimum = password.length >= MIN_LENGTH;
  let score: PasswordStrength = 'weak';
  let label = 'Weak';
  let percent = 20;

  if (!meetsMinimum) {
    score = 'weak';
    label = 'Too short';
    percent = Math.min(25, Math.round((password.length / MIN_LENGTH) * 25));
  } else if (points <= 2) {
    score = 'fair';
    label = 'Fair';
    percent = 45;
  } else if (points === 3) {
    score = 'good';
    label = 'Good';
    percent = 70;
  } else {
    score = 'strong';
    label = 'Strong';
    percent = 100;
  }

  return { score, label, percent, meetsMinimum, hints };
}

export function generateTemporaryPassword(length = 14): string {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  const lower = 'abcdefghijkmnopqrstuvwxyz';
  const digits = '23456789';
  const symbols = '!@#$%&*';
  const all = upper + lower + digits + symbols;

  const pick = (chars: string) => chars[Math.floor(Math.random() * chars.length)];
  const required = [pick(upper), pick(lower), pick(digits), pick(symbols)];
  const rest = Array.from({ length: Math.max(length - required.length, 0) }, () => pick(all));
  const combined = [...required, ...rest];

  for (let i = combined.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [combined[i], combined[j]] = [combined[j], combined[i]];
  }

  return combined.join('');
}
