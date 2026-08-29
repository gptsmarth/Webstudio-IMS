import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, Laptop, MousePointer2 } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { isAccessoryModel } from '../../lib/productCategory';
import { buildStockModelSpecLines, stockAvailabilityLabel } from '../../lib/stockModelCard';
import { useProductImage } from '../../hooks/useProductImage';

interface StockModelRowProps {
  row: ModelInventoryRow;
  onSelect: () => void;
  hideBrand?: boolean;
}

export function StockModelRow({
  row,
  onSelect,
  hideBrand = true,
}: StockModelRowProps): JSX.Element {
  const [imageBroken, setImageBroken] = useState(false);
  const image = useProductImage(row.model.id, {
    remoteUrl: row.model.product_image_url,
    brandName: row.model.brand_name,
    modelName: row.model.model_name,
  });
  const specLines = useMemo(() => buildStockModelSpecLines(row.model), [row.model]);
  const inStock = row.availableUnits > 0;
  const specPreview = useMemo(
    () =>
      specLines
        .slice(0, 4)
        .map((line) => line.value)
        .join(' · '),
    [specLines],
  );
  const showImage = !image.loading && !image.failed && !imageBroken;

  useEffect(() => {
    setImageBroken(false);
  }, [image.src]);

  return (
    <button
      type="button"
      className={`stock-model-row${inStock ? '' : ' stock-model-row--empty'}`}
      onClick={onSelect}
    >
      <div className="stock-model-row__media">
        {image.loading ? (
          <div className="stock-model-row__image stock-model-row__image--placeholder skeleton" />
        ) : showImage ? (
          <img
            src={image.src}
            alt={row.model.model_name}
            className="stock-model-row__image"
            loading="lazy"
            onError={() => setImageBroken(true)}
          />
        ) : (
          <div className="stock-model-row__image stock-model-row__image--placeholder" aria-hidden>
            {isAccessoryModel(row.model) ? (
              <MousePointer2 size={28} strokeWidth={1.25} />
            ) : (
              <Laptop size={28} strokeWidth={1.25} />
            )}
          </div>
        )}
      </div>

      <div className="stock-model-row__main">
        {!hideBrand && row.model.brand_name && (
          <p className="stock-model-row__brand">{row.model.brand_name}</p>
        )}
        <h3 className="stock-model-row__name">{row.model.model_name}</h3>
        <p className="stock-model-row__number col-mono">{row.model.model_number}</p>
        <p className="stock-model-row__specs">{specPreview}</p>
      </div>

      <div className="stock-model-row__aside">
        <span
          className={`stock-model-row__badge${inStock ? ' stock-model-row__badge--in' : ' stock-model-row__badge--out'}`}
        >
          {inStock ? 'In stock' : 'Out of stock'}
        </span>
        <span className="stock-model-row__units">{stockAvailabilityLabel(row.availableUnits)}</span>
        <span className="stock-model-row__cta">
          View details
          <ChevronRight size={14} aria-hidden />
        </span>
      </div>
    </button>
  );
}
