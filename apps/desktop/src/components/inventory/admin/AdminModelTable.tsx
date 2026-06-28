import type { ModelInventoryRow } from '../../../lib/inventoryHierarchy';
import { formatInventorySpecsTable } from '../../../lib/inventory';
import { formatInventoryPrice } from '../../../lib/inventoryPrice';

interface AdminModelTableProps {
  rows: ModelInventoryRow[];
  loading?: boolean;
  onSelect: (modelId: string, label: string) => void;
  onAddLaptop: () => void;
  onEditModel: (modelId: string) => void;
}

export function AdminModelTable({
  rows,
  loading,
  onSelect,
  onAddLaptop,
  onEditModel,
}: AdminModelTableProps): JSX.Element {
  if (loading) {
    return (
      <div className="admin-model-table-section">
        <div className="admin-model-table__toolbar">
          <button type="button" className="btn btn-primary btn-sm" disabled>
            Add laptop
          </button>
        </div>
        <div className="skeleton admin-model-table__skeleton" />
      </div>
    );
  }

  return (
    <div className="admin-model-table-section">
      <div className="admin-model-table__toolbar">
        <button type="button" className="btn btn-primary btn-sm" onClick={onAddLaptop}>
          Add laptop
        </button>
      </div>
      <div className="admin-model-table-wrap">
        <table className="table-root admin-model-table">
          <thead>
            <tr>
              <th>Model number</th>
              <th>Name</th>
              <th>Configuration</th>
              <th className="admin-model-table__num">Selling price</th>
              <th className="admin-model-table__num">Purchase price</th>
              <th className="admin-model-table__num">Available</th>
              <th className="admin-model-table__num">Sold</th>
              <th>Status</th>
              <th className="admin-model-table__actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="admin-model-table__empty">
                  No models for this brand yet. Use Add laptop to register the first model.
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr
                key={row.model.id}
                className="admin-model-table__row"
                onClick={() => onSelect(row.model.id, `${row.model.model_number} · ${row.model.model_name}`)}
              >
                <td className="col-mono admin-model-table__model-number">{row.model.model_number}</td>
                <td className="admin-model-table__name">{row.model.model_name}</td>
                <td className="admin-model-table__config">{formatInventorySpecsTable(row.model)}</td>
                <td className="admin-model-table__num">{formatInventoryPrice(row.model.selling_price)}</td>
                <td className="admin-model-table__num">{formatInventoryPrice(row.model.purchase_price)}</td>
                <td className="admin-model-table__num">{row.availableUnits}</td>
                <td className="admin-model-table__num">{row.soldUnits}</td>
                <td>
                  <span className={`badge ${row.availableUnits === 0 ? 'badge-warning' : 'badge-success'}`}>
                    {row.availableUnits === 0 ? 'Zero availability' : 'In stock'}
                  </span>
                </td>
                <td className="admin-model-table__actions" onClick={(event) => event.stopPropagation()}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => onEditModel(row.model.id)}
                  >
                    Edit model
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
