import { useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Archive,
  Eye,
  KeyRound,
  LogOut,
  Pencil,
  RotateCcw,
  Shield,
  ToggleLeft,
  ToggleRight,
  Unlock,
} from 'lucide-react';
import {
  canArchiveUser,
  canChangeRole,
  canDisableUser,
  canEnableUser,
  canRestoreUser,
} from '../../lib/users';
import { P, PermissionService, permissionDeniedTooltip } from '../../services/PermissionService';
import type { UserSummary } from '../../services/api/UserService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

export type UserRowAction =
  | 'view'
  | 'edit'
  | 'reset-password'
  | 'disable'
  | 'enable'
  | 'change-role'
  | 'unlock'
  | 'force-logout'
  | 'archive'
  | 'restore';

interface UserRowActionsMenuProps {
  user: UserSummary;
  anchorRect: DOMRect;
  currentUserId: number | null;
  activeMainAdminCount: number;
  permissions: string[];
  onAction: (action: UserRowAction) => void;
  onClose: () => void;
}

export function UserRowActionsMenu({
  user,
  anchorRect,
  currentUserId,
  activeMainAdminCount,
  permissions,
  onAction,
  onClose,
}: UserRowActionsMenuProps): JSX.Element {
  const menuRef = useRef<HTMLDivElement>(null);
  const ps = PermissionService.from(permissions);
  const disableCheck = canDisableUser(user, currentUserId, activeMainAdminCount);
  const archiveCheck = canArchiveUser(user, currentUserId, activeMainAdminCount);
  const roleCheck = canChangeRole(user, currentUserId, activeMainAdminCount);
  const canView = ps.has(P.users.view);
  const canEdit = ps.has(P.users.edit);
  const canReset = ps.has(P.users.resetPassword);
  const canChangeRolePerm = ps.has(P.users.edit);
  const canDeactivate = ps.has(P.users.deactivate);
  const canActivate = ps.has(P.users.activate);

  useRowActionsMenuDismiss(menuRef, onClose);

  const { top, left } = rowMenuPosition(anchorRect, 280);

  if (!canView) {
    return <></>;
  }

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
      <button
        type="button"
        className="usr-row-menu__item"
        role="menuitem"
        disabled={!canEdit}
        title={canEdit ? undefined : permissionDeniedTooltip(P.users.edit)}
        onClick={() => onAction('edit')}
      >
        <Pencil size={14} aria-hidden /> Edit user
      </button>
      <button
        type="button"
        className="usr-row-menu__item"
        role="menuitem"
        disabled={!canReset}
        title={canReset ? undefined : permissionDeniedTooltip(P.users.resetPassword)}
        onClick={() => onAction('reset-password')}
      >
        <KeyRound size={14} aria-hidden /> Reset password
      </button>
      {user.is_locked && (
        <button
          type="button"
          className="usr-row-menu__item"
          role="menuitem"
          disabled={!canEdit}
          title={canEdit ? undefined : permissionDeniedTooltip(P.users.edit)}
          onClick={() => onAction('unlock')}
        >
          <Unlock size={14} aria-hidden /> Unlock user
        </button>
      )}
      {user.active_session_count > 0 && (
        <button
          type="button"
          className="usr-row-menu__item"
          role="menuitem"
          disabled={!canEdit}
          title={canEdit ? undefined : permissionDeniedTooltip(P.users.edit)}
          onClick={() => onAction('force-logout')}
        >
          <LogOut size={14} aria-hidden /> Force logout
        </button>
      )}
      <button
        type="button"
        className="usr-row-menu__item"
        role="menuitem"
        disabled={!canChangeRolePerm || !roleCheck.allowed}
        title={!canChangeRolePerm ? permissionDeniedTooltip(P.users.edit) : roleCheck.reason}
        onClick={() => onAction('change-role')}
      >
        <Shield size={14} aria-hidden /> Change access
      </button>
      {!user.is_archived && user.status === 'active' ? (
        <button
          type="button"
          className="usr-row-menu__item usr-row-menu__item--danger"
          role="menuitem"
          disabled={!canDeactivate || !disableCheck.allowed}
          title={!canDeactivate ? permissionDeniedTooltip(P.users.deactivate) : disableCheck.reason}
          onClick={() => onAction('disable')}
        >
          <ToggleLeft size={14} aria-hidden /> Deactivate
        </button>
      ) : (
        !user.is_archived && (
          <button
            type="button"
            className="usr-row-menu__item"
            role="menuitem"
            disabled={!canActivate || !canEnableUser(user)}
            title={!canActivate ? permissionDeniedTooltip(P.users.activate) : undefined}
            onClick={() => onAction('enable')}
          >
            <ToggleRight size={14} aria-hidden /> Activate
          </button>
        )
      )}
      {!user.is_archived && (
        <button
          type="button"
          className="usr-row-menu__item usr-row-menu__item--danger"
          role="menuitem"
          disabled={!canDeactivate || !archiveCheck.allowed}
          title={!canDeactivate ? permissionDeniedTooltip(P.users.deactivate) : archiveCheck.reason}
          onClick={() => onAction('archive')}
        >
          <Archive size={14} aria-hidden /> Archive
        </button>
      )}
      {canRestoreUser(user) && (
        <button
          type="button"
          className="usr-row-menu__item"
          role="menuitem"
          disabled={!canActivate}
          title={!canActivate ? permissionDeniedTooltip(P.users.activate) : undefined}
          onClick={() => onAction('restore')}
        >
          <RotateCcw size={14} aria-hidden /> Restore
        </button>
      )}
    </div>,
    document.body,
  );
}
