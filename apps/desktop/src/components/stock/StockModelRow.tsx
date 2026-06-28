import { useEffect, useMemo, useState } from 'react';
import { ChevronRight, Laptop } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { buildStockModelSpecLines, stockAvailabilityLabel } from '../../lib/stockModelCard';
import { ProductImageService } from '../../services/images/ProductImageService';

interface StockModelRowProps {
  row: ModelInventoryRow;
  onSelect: () => void;
  hideBrand?: boolean;
}

export function StockModelRow({ row, onSelect, hideBrand = true }: StockModelRowProps): JSX.Element {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const specLines = useMemo(() => buildStockModelSpecLines(row.model), [row.model]);
  const inStock = row.availableUnits > 0;
  const specPreview = useMemo(
    () => specLines.slice(0, 4).map((line) => line.value).join(' · '),
    [specLines],
  );

  useEffect(() => {
    let cancelled = false;
    setImageLoading(true);
    setImageFailed(false);
    void ProductImageService.resolve(row.model.id, {
      remoteUrl: row.model.product_image_url,
      brandName: row.model.brand_name,
      modelName: row.model.model_name,
    }).then((result) => {
      if (!cancelled) {
        setImageSrc(result.src);
        setImageFailed(result.source === 'placeholder');
        setImageLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [row.model.brand_name, row.model.id, row.model.model_name, row.model.product_image_url]);

  return (
    <button type="button" className={`stock-model-row${inStock ? '' : ' stock-model-row--empty'}`} onClick={onSelect}>
      <div className="stock-model-row__media">
        {imageLoading ? (
          <div className="stock-model-row__image stock-model-row__image--placeholder skeleton" />
        ) : imageSrc && !imageFailed ? (
          <img
            src={imageSrc}
            alt={row.model.model_name}
            className="stock-model-row__image"
            loading="lazy"
            onError={() => {
              setImageFailed(true);
              setImageSrc(ProductImageService.getPlaceholderSrc());
            }}
          />
        ) : (
          <div className="stock-model-row__image stock-model-row__image--placeholder" aria-hidden>
            <Laptop size={28} strokeWidth={1.25} />
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
        <span className={`stock-model-row__badge${inStock ? ' stock-model-row__badge--in' : ' stock-model-row__badge--out'}`}>
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
