/**
 * Shared auth package stub for Flutter/mobile clients.
 * Permission strings remain defined in backend `permissions.py` and desktop `PermissionService.ts`.
 * Future: export PERMISSION_REGISTRY metadata from `userPermissions.ts` for cross-platform UI.
 */
export const PERMISSIONS = {} as const;

export type PermissionGrantSource = 'role' | 'override' | 'license';
