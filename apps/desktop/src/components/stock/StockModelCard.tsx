import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Laptop } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import {
  buildStockModelSpecLines,
  pickStockCardHighlightSpecs,
  stockAvailabilityLabel,
} from '../../lib/stockModelCard';
import { ProductImageService } from '../../services/images/ProductImageService';

interface StockModelCardProps {
  row: ModelInventoryRow;
  onSelect: () => void;
}

export function StockModelCard({ row, onSelect }: StockModelCardProps): JSX.Element {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const highlightSpecs = useMemo(
    () => pickStockCardHighlightSpecs(buildStockModelSpecLines(row.model)),
    [row.model],
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
    <article className="stock-model-card">
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
            {row.model.brand_name && (
              <p className="stock-model-card__brand">{row.model.brand_name}</p>
            )}
            <h3 className="stock-model-card__name">{row.model.model_name}</h3>
            <p className="stock-model-card__number col-mono">{row.model.model_number}</p>
          </div>

          {highlightSpecs.length > 0 && (
            <dl className="stock-model-card__spec-grid">
              {highlightSpecs.map((line) => (
                <div key={line.label} className="stock-model-card__spec-row">
                  <dt>{line.label}</dt>
                  <dd>{line.value}</dd>
                </div>
              ))}
            </dl>
          )}

          <div className="stock-model-card__footer">
            <span className="stock-model-card__availability badge badge-success">
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
