import { userInitials } from '../../lib/users';

interface UserAvatarProps {
  user: { username: string; display_name?: string | null };
  size?: 'sm' | 'md';
}

export function UserAvatar({ user, size = 'sm' }: UserAvatarProps): JSX.Element {
  return (
    <span className={`usr-avatar usr-avatar--${size}`} aria-hidden>
      {userInitials(user)}
    </span>
  );
}
