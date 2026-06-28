import { BrandLogoRegistry } from '../../registries/BrandLogoRegistry';

interface InventoryBrandCellProps {
  brandName: string;
}

export function InventoryBrandCell({ brandName }: InventoryBrandCellProps): JSX.Element {
  const logoSrc = BrandLogoRegistry.getLogo(brandName);

  return (
    <span className="inv-brand-cell" data-brand={brandName.trim().toLowerCase()}>
      <img src={logoSrc} alt="" className="inv-brand-logo" loading="lazy" />
      <span className="inv-brand-name">{brandName}</span>
    </span>
  );
}
