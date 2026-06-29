/**
 * Future RBAC extension points — custom roles, overrides, and effective permission resolution.
 * Not implemented; desktop and Flutter clients can adopt these types when backend support ships.
 */

export type PermissionGrantSource = 'role' | 'override' | 'license';

/** Future: grant or deny a single permission for a specific user. */
export interface PermissionOverride {
  userId: number;
  permission: string;
  granted: boolean;
  reason?: string;
  expiresAt?: string | null;
}

/** Future: organisation-defined role with a custom permission set. */
export interface CustomRoleDefinition {
  id: string;
  name: string;
  permissions: string[];
  basedOnRole?: string;
}

export interface EffectivePermissionGrant {
  permission: string;
  source: PermissionGrantSource;
  /** Role name, override id, or license tier label. */
  inheritedFrom: string;
}

/**
 * Resolve effective permissions for a user.
 * Today: static role map only. Overrides and license filtering are passthrough hooks.
 */
export function resolveEffectivePermissions(input: {
  rolePermissions: string[];
  roleLabel: string;
  overrides?: PermissionOverride[];
  licenseFiltered?: string[];
}): EffectivePermissionGrant[] {
  const base = input.licenseFiltered ?? input.rolePermissions;
  const overrideMap = new Map(
    (input.overrides ?? []).map((entry) => [entry.permission, entry]),
  );

  const resolved = new Set(base);
  for (const override of overrideMap.values()) {
    if (override.granted) resolved.add(override.permission);
    else resolved.delete(override.permission);
  }

  return [...resolved].sort().map((permission) => {
    const override = overrideMap.get(permission);
    if (override) {
      return {
        permission,
        source: 'override' as const,
        inheritedFrom: override.reason ?? 'Custom override',
      };
    }
    if (input.licenseFiltered && !input.licenseFiltered.includes(permission)) {
      return {
        permission,
        source: 'license' as const,
        inheritedFrom: 'License',
      };
    }
    return {
      permission,
      source: 'role' as const,
      inheritedFrom: input.roleLabel,
    };
  });
}
