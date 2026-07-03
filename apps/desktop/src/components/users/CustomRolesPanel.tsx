import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Plus, Trash2 } from 'lucide-react';
import {
  AccessRoleService,
  type CustomAccessRoleDetail,
  type CustomAccessRoleSummary,
} from '../../services/api/AccessRoleService';
import { PermissionMatrixEditor } from './PermissionMatrixEditor';

interface CustomRolesPanelProps {
  onRolesChanged?: () => void;
}

export function CustomRolesPanel({ onRolesChanged }: CustomRolesPanelProps): JSX.Element {
  const [roles, setRoles] = useState<CustomAccessRoleSummary[]>([]);
  const [catalog, setCatalog] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<CustomAccessRoleDetail | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [permissions, setPermissions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [roleList, permissionCatalog] = await Promise.all([
        AccessRoleService.listRoles(true),
        AccessRoleService.listCatalog(),
      ]);
      setRoles(roleList);
      setCatalog(permissionCatalog);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load access roles.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openCreate = () => {
    setEditing(null);
    setName('');
    setDescription('');
    setPermissions([]);
    setEditorOpen(true);
  };

  const openEdit = async (role: CustomAccessRoleSummary) => {
    setSaving(true);
    try {
      const detail = await AccessRoleService.getRole(role.id);
      setEditing(detail);
      setName(detail.name);
      setDescription(detail.description ?? '');
      setPermissions(detail.permissions);
      setEditorOpen(true);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load access role.');
    } finally {
      setSaving(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      if (editing) {
        await AccessRoleService.updateRole(editing.id, {
          name,
          description,
          permissions,
        });
      } else {
        await AccessRoleService.createRole({ name, description, permissions });
      }
      setEditorOpen(false);
      await refresh();
      onRolesChanged?.();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to save access role.');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (role: CustomAccessRoleSummary) => {
    if (!window.confirm(`Delete access role "${role.name}"?`)) return;
    setSaving(true);
    try {
      await AccessRoleService.deleteRole(role.id);
      await refresh();
      onRolesChanged?.();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to delete access role.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="usr-access-roles">
      <header className="usr-access-roles__header">
        <div>
          <h2 className="usr-access-roles__title">Custom access roles</h2>
          <p className="usr-access-roles__subtitle">
            Name a role and choose exactly which sections each user can view, create, edit, or
            export.
          </p>
        </div>
        <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
          <Plus size={14} aria-hidden />
          New role
        </button>
      </header>

      {error && (
        <div className="alert alert-danger usr-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <p>Loading access roles…</p>
      ) : (
        <div className="usr-access-roles__list">
          {roles.length === 0 ? (
            <p className="usr-empty__text">
              No custom roles yet. Create one to assign granular access.
            </p>
          ) : (
            roles.map((role) => (
              <div key={role.id} className="usr-access-roles__card">
                <div>
                  <strong>{role.name}</strong>
                  {role.description && <p>{role.description}</p>}
                  <p className="usr-access-roles__meta">
                    {role.permission_count} permissions · {role.assigned_user_count} users
                    {!role.is_active && ' · Inactive'}
                  </p>
                </div>
                <div className="usr-access-roles__actions">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void openEdit(role)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={role.assigned_user_count > 0 || saving}
                    onClick={() => void remove(role)}
                  >
                    <Trash2 size={14} aria-hidden />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {editorOpen && (
        <div
          className="cat-dialog-overlay"
          role="presentation"
          onClick={() => setEditorOpen(false)}
        >
          <div
            className="cat-dialog cat-dialog--permissions animate-slide-in"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="cat-dialog__header">
              <h2 className="cat-dialog__title">
                {editing ? 'Edit access role' : 'New access role'}
              </h2>
            </header>
            <div className="cat-dialog__body">
              <label className="cat-field">
                <span>Role name</span>
                <input
                  className="input"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <label className="cat-field">
                <span>Description</span>
                <input
                  className="input"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
              <PermissionMatrixEditor
                catalog={catalog}
                selected={permissions}
                onChange={setPermissions}
              />
            </div>
            <footer className="cat-dialog__footer">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setEditorOpen(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => void save()}
                disabled={saving || !name.trim()}
              >
                {saving ? 'Saving…' : 'Save role'}
              </button>
            </footer>
          </div>
        </div>
      )}
    </section>
  );
}
