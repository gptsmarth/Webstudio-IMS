import { BrandLogoRegistry } from '../../registries/BrandLogoRegistry';
import type { DistributionGroup } from '../../services/api/DashboardService';
import { DashboardEmptyState } from './DashboardWidget';

interface DashboardBrandDistributionProps {
  brands: DistributionGroup[];
  loading: boolean;
}

export function DashboardBrandDistribution({ brands, loading }: DashboardBrandDistributionProps): JSX.Element {
  if (loading) {
    return (
      <div className="dash-brand-table-wrap">
        <table className="table-root dash-brand-table">
          <tbody>
            {Array.from({ length: 4 }, (_, index) => (
              <tr key={index}>
                <td colSpan={3}><div className="skeleton dash-brand-table__skeleton" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const rows = [...brands].sort((a, b) => b.available - a.available);

  if (rows.length === 0) {
    return (
      <DashboardEmptyState
        title="No brand distribution"
        description="Brand availability will appear once inventory is recorded."
      />
    );
  }

  return (
    <div className="dash-brand-table-wrap">
      <table className="table-root dash-brand-table">
        <thead>
          <tr>
            <th>Brand</th>
            <th>Available</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((brand) => (
            <tr key={brand.id}>
              <td>
                <span className="dash-brand-table__brand">
                  <img src={BrandLogoRegistry.getLogo(brand.name)} alt="" className="dash-brand-table__logo" />
                  <span>{brand.name}</span>
                </span>
              </td>
              <td className="col-amount">{brand.available.toLocaleString()}</td>
              <td className="col-amount">{brand.total.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
