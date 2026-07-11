import { P, PermissionService } from '../services/PermissionService';

/** Stable dependency key so session object identity changes do not re-fetch. */
export function permissionsDependencyKey(permissions: string[]): string {
  return permissions.join('|');
}

/** Shared fetch gates for catalogue / reference APIs used across workspace tabs. */
export function referenceDataFetchPlan(permissions: string[]) {
  const permissionService = PermissionService.from(permissions);
  const hasInventoryAccess =
    permissionService.has(P.inventory.view) ||
    permissionService.has(P.inventory.create) ||
    permissionService.has(P.inventory.transfer) ||
    permissionService.has(P.inventory.stockEdit);
  const hasSalesAccess = permissionService.has(P.sales.view);
  const hasReportsAccess = permissionService.has(P.reports.view);
  const hasAuditAccess = permissionService.has(P.audit.view);

  return {
    needsBrands:
      permissionService.has(P.brands.view) ||
      hasInventoryAccess ||
      hasSalesAccess ||
      hasReportsAccess,
    needsLocations:
      permissionService.has(P.locations.view) ||
      hasInventoryAccess ||
      hasSalesAccess ||
      hasReportsAccess ||
      hasAuditAccess,
    needsProductModels:
      permissionService.has(P.productModels.view) ||
      hasInventoryAccess ||
      hasSalesAccess ||
      hasReportsAccess,
    needsInventoryItems: permissionService.has(P.inventory.view),
    needsDistribution:
      permissionService.has(P.inventory.view) ||
      permissionService.has(P.brands.view) ||
      permissionService.has(P.reports.view),
    needsUsers: permissionService.has(P.users.view),
    needsAudit: permissionService.has(P.audit.view),
    needsInventoryAudit:
      permissionService.has(P.audit.view) || permissionService.has(P.audit.lifecycle),
  };
}
