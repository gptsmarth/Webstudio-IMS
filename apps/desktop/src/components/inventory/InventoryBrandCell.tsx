import { BrandLogoImage } from '../branding/BrandLogoImage';

interface InventoryBrandCellProps {
  brandName: string;
  logoFilename?: string | null;
}

export function InventoryBrandCell({
  brandName,
  logoFilename,
}: InventoryBrandCellProps): JSX.Element {
  return (
    <span className="inv-brand-cell" data-brand={brandName.trim().toLowerCase()}>
      <BrandLogoImage brand={brandName} logoFilename={logoFilename} className="inv-brand-logo" />
      <span className="inv-brand-name">{brandName}</span>
    </span>
  );
}
