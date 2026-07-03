/**
 * License-aware permission extension points (not implemented).
 * Permission strings and backend APIs are unchanged; this module is a future hook only.
 */

export interface LicensePermissionContext {
  licenseTier: string | null;
  isPermissionLicensed: (permission: string) => boolean;
}

/** Passthrough until licensing is implemented. */
export function createLicensePermissionContext(
  licenseTier: string | null = null,
): LicensePermissionContext {
  return {
    licenseTier,
    isPermissionLicensed: () => true,
  };
}

/** Filter permissions by license entitlements. Currently returns the input unchanged. */
export function filterPermissionsByLicense(
  permissions: string[],
  _context: LicensePermissionContext,
): string[] {
  return permissions;
}

/** Whether a permission should appear in UI for the current license tier. */
export function isPermissionVisibleForLicense(
  _permission: string,
  _context: LicensePermissionContext,
): boolean {
  return true;
}
