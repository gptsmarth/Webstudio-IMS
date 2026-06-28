import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Laptop, Pencil } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { formatInventoryPrice } from '../../lib/inventoryPrice';
import {
  buildStockModelSpecLines,
  stockAvailabilityLabel,
} from '../../lib/stockModelCard';
import { ProductImageService } from '../../services/images/ProductImageService';

interface StockModelCardProps {
  row: ModelInventoryRow;
  showPrice?: boolean;
  canEditPrice?: boolean;
  onSelect: () => void;
  onEditPrice?: () => void;
}

export function StockModelCard({
  row,
  showPrice = false,
  canEditPrice = false,
  onSelect,
  onEditPrice,
}: StockModelCardProps): JSX.Element {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const specLines = useMemo(() => buildStockModelSpecLines(row.model), [row.model]);
  const inStock = row.availableUnits > 0;

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
    <article className="stock-model-card">
      <div className="stock-model-card__status-row">
        <span className={`stock-model-card__status ${inStock ? 'stock-model-card__status--in' : 'stock-model-card__status--out'}`}>
          <span className="stock-model-card__status-dot" aria-hidden />
          {inStock ? 'In stock' : 'Out of stock'}
        </span>
        {canEditPrice && onEditPrice && (
          <button
            type="button"
            className="stock-model-card__edit-price"
            aria-label={`Edit selling price for ${row.model.model_number}`}
            onClick={(event) => {
              event.stopPropagation();
              onEditPrice();
            }}
          >
            <Pencil size={14} aria-hidden />
            Edit price
          </button>
        )}
      </div>

      <button type="button" className="stock-model-card__main" onClick={onSelect}>
        <div className="stock-model-card__media">
          {imageLoading ? (
            <div className="stock-model-card__image stock-model-card__image--placeholder skeleton" />
          ) : imageSrc && !imageFailed ? (
            <img
              src={imageSrc}
              alt={row.model.model_name}
              className="stock-model-card__image"
              loading="lazy"
              onError={() => {
                setImageFailed(true);
                setImageSrc(ProductImageService.getPlaceholderSrc());
              }}
            />
          ) : (
            <div className="stock-model-card__image stock-model-card__image--placeholder" aria-hidden>
              <Laptop size={48} strokeWidth={1.15} />
            </div>
          )}
        </div>

        <div className="stock-model-card__body">
          <div className="stock-model-card__intro">
            <h3 className="stock-model-card__number col-mono">{row.model.model_number}</h3>
            <p className="stock-model-card__name">
              {row.model.brand_name ? `${row.model.brand_name} ` : ''}
              {row.model.model_name}
            </p>
          </div>

          {showPrice && (
            <div className="stock-model-card__price-block">
              <p className="stock-model-card__price-label">Price starting at</p>
              <p className="stock-model-card__price">
                {formatInventoryPrice(row.model.selling_price)}
              </p>
            </div>
          )}

          {specLines.length > 0 && (
            <ul className="stock-model-card__spec-list">
              {specLines.map((line) => (
                <li key={line.label} className="stock-model-card__spec-item">
                  <span className="stock-model-card__spec-bullet" aria-hidden />
                  <span>
                    <strong>{line.label}:</strong> {line.value}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <div className="stock-model-card__footer">
            <span className={`stock-model-card__availability badge ${inStock ? 'badge-success' : 'badge-warning'}`}>
              {stockAvailabilityLabel(row.availableUnits)}
            </span>
            <span className="stock-model-card__cta">
              View units
              <ArrowRight size={14} aria-hidden />
            </span>
          </div>
        </div>
      </button>
    </article>
  );
}
