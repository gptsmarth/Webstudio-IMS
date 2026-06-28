import { useEffect, useState } from 'react';
import {
  fetchAllInventoryForModel,
  summarizeProductModelUnits,
  type ProductModelUnitSummary,
} from '../../lib/productModelSummary';
import type { ProductModel } from '../../services/api/ProductModelService';

interface ProductModelSummaryPanelProps {
  model: ProductModel | null;
}

export function ProductModelSummaryPanel({ model }: ProductModelSummaryPanelProps): JSX.Element | null {
  const [summary, setSummary] = useState<ProductModelUnitSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!model?.id) {
      setSummary(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    void fetchAllInventoryForModel(model.id)
      .then((items) => {
        if (cancelled) return;
        setSummary(summarizeProductModelUnits(items));
      })
      .catch(() => {
        if (cancelled) return;
        setError('Unable to load unit summary.');
        setSummary(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [model?.id]);

  if (!model) return null;

  return (
    <div className="inv-model-summary">
      <p className="inv-model-summary__title">
        Existing catalogue model — {model.model_number} · {model.model_name}
      </p>
      {loading && <div className="skeleton inv-model-summary__skeleton" />}
      {error && <p className="inv-model-summary__error">{error}</p>}
      {!loading && !error && summary && (
        <>
          <dl className="inv-model-summary__stats">
            <div>
              <dt>Total units</dt>
              <dd>{summary.totalUnits}</dd>
            </div>
            <div>
              <dt>Available</dt>
              <dd>{summary.availableUnits}</dd>
            </div>
            <div>
              <dt>Sold</dt>
              <dd>{summary.soldUnits}</dd>
            </div>
          </dl>
          <div className="inv-model-summary__locations">
            <p className="inv-model-summary__locations-title">Units by location</p>
            {summary.byLocation.length === 0 ? (
              <p className="inv-model-summary__muted">No unsold units on record.</p>
            ) : (
              <ul className="inv-model-summary__location-list">
                {summary.byLocation.map((row) => (
                  <li key={row.locationId}>
                    <span>{row.locationName}</span>
                    <span className="inv-model-summary__count">{row.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="inv-model-summary__hint">
            New serial numbers will be linked to this product model — not a duplicate catalogue entry.
          </p>
        </>
      )}
    </div>
  );
}
