import { useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Eye,
  KeyRound,
  Pencil,
  Shield,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import {
  canChangeRole,
  canDisableUser,
  canEnableUser,
} from '../../lib/users';
import type { UserDetail } from '../../services/api/UserService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

export type UserRowAction =
  | 'view'
  | 'edit'
  | 'reset-password'
  | 'disable'
  | 'enable'
  | 'change-role';

interface UserRowActionsMenuProps {
  user: UserDetail | { id: number; username: string; role: UserDetail['role']; status: UserDetail['status'] };
  anchorRect: DOMRect;
  currentUserId: number | null;
  activeMainAdminCount: number;
  onAction: (action: UserRowAction) => void;
  onClose: () => void;
}

export function UserRowActionsMenu({
  user,
  anchorRect,
  currentUserId,
  activeMainAdminCount,
  onAction,
  onClose,
}: UserRowActionsMenuProps): JSX.Element {
  const menuRef = useRef<HTMLDivElement>(null);
  const disableCheck = canDisableUser(user as UserDetail, currentUserId, activeMainAdminCount);
  const roleCheck = canChangeRole(user as UserDetail, currentUserId, activeMainAdminCount);

  useRowActionsMenuDismiss(menuRef, onClose);

  const { top, left } = rowMenuPosition(anchorRect, 280);

  return createPortal(
    <div
      ref={menuRef}
      className="row-actions-menu usr-row-menu"
      style={{ top, left }}
      role="menu"
      aria-label={`Actions for ${user.username}`}
    >
      <button type="button" className="usr-row-menu__item" role="menuitem" onClick={() => onAction('view')}>
        <Eye size={14} aria-hidden /> View details
      </button>
      <button type="button" className="usr-row-menu__item" role="menuitem" onClick={() => onAction('edit')}>
        <Pencil size={14} aria-hidden /> Edit user
      </button>
      <button type="button" className="usr-row-menu__item" role="menuitem" onClick={() => onAction('reset-password')}>
        <KeyRound size={14} aria-hidden /> Reset password
      </button>
      <button
        type="button"
        className="usr-row-menu__item"
        role="menuitem"
        disabled={!roleCheck.allowed}
        title={roleCheck.reason}
        onClick={() => onAction('change-role')}
      >
        <Shield size={14} aria-hidden /> Change role
      </button>
      {user.status === 'active' ? (
        <button
          type="button"
          className="usr-row-menu__item usr-row-menu__item--danger"
          role="menuitem"
          disabled={!disableCheck.allowed}
          title={disableCheck.reason}
          onClick={() => onAction('disable')}
        >
          <ToggleLeft size={14} aria-hidden /> Disable user
        </button>
      ) : (
        <button
          type="button"
          className="usr-row-menu__item"
          role="menuitem"
          disabled={!canEnableUser(user as UserDetail)}
          onClick={() => onAction('enable')}
        >
          <ToggleRight size={14} aria-hidden /> Enable user
        </button>
      )}
    </div>,
    document.body,
  );
}
