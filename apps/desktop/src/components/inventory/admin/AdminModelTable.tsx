import { forwardRef } from 'react';
import type { ModelInventoryRow } from '../../../lib/inventoryHierarchy';
import { formatInventorySpecsTable } from '../../../lib/inventory';
import { formatInventoryPrice } from '../../../lib/inventoryPrice';
import {
  accessoryKindLabel,
  isAccessoryModel,
  productCategoryLabel,
} from '../../../lib/productCategory';

interface AdminModelTableProps {
  rows: ModelInventoryRow[];
  loading?: boolean;
  onSelect: (modelId: string, label: string) => void;
  onAddLaptop: () => void;
  onAddAccessory: () => void;
  onEditModel: (modelId: string) => void;
}

export const AdminModelTable = forwardRef<HTMLDivElement, AdminModelTableProps>(
  function AdminModelTable(
    { rows, loading, onSelect, onAddLaptop, onAddAccessory, onEditModel },
    ref,
  ) {
    return (
      <div className="admin-model-table-section">
        <div className="admin-model-table__toolbar">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onAddLaptop}
            disabled={loading}
          >
            Add laptop
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onAddAccessory}
            disabled={loading}
          >
            Add accessory
          </button>
        </div>
        <div ref={ref} className="admin-model-table-wrap">
          {loading ? (
            <div className="skeleton admin-model-table__skeleton" />
          ) : (
            <table className="table-root admin-model-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Model / part number</th>
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
                    <td colSpan={10} className="admin-model-table__empty">
                      No models for this brand yet. Use Add laptop or Add accessory to register
                      stock.
                    </td>
                  </tr>
                )}
                {rows.map((row) => (
                  <tr
                    key={row.model.id}
                    className="admin-model-table__row"
                    onClick={() =>
                      onSelect(row.model.id, `${row.model.model_number} · ${row.model.model_name}`)
                    }
                  >
                    <td className="admin-model-table__type">
                      {isAccessoryModel(row.model)
                        ? accessoryKindLabel(row.model.accessory_kind)
                        : productCategoryLabel(row.model.category)}
                    </td>
                    <td className="col-mono admin-model-table__model-number">
                      {row.model.part_number && row.model.part_number !== row.model.model_number
                        ? `${row.model.model_number} · PN ${row.model.part_number}`
                        : row.model.model_number}
                    </td>
                    <td className="admin-model-table__name">{row.model.model_name}</td>
                    <td className="admin-model-table__config">
                      {formatInventorySpecsTable(row.model)}
                    </td>
                    <td className="admin-model-table__num">
                      {formatInventoryPrice(row.model.selling_price)}
                    </td>
                    <td className="admin-model-table__num">
                      {formatInventoryPrice(row.model.purchase_price)}
                    </td>
                    <td className="admin-model-table__num">{row.availableUnits}</td>
                    <td className="admin-model-table__num">{row.soldUnits}</td>
                    <td>
                      <span
                        className={`badge ${row.availableUnits === 0 ? 'badge-warning' : 'badge-success'}`}
                      >
                        {row.availableUnits === 0 ? 'Zero availability' : 'In stock'}
                      </span>
                    </td>
                    <td
                      className="admin-model-table__actions"
                      onClick={(event) => event.stopPropagation()}
                    >
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
          )}
        </div>
      </div>
    );
  },
);
