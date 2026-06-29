import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, Laptop } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { formatInventoryPrice } from '../../lib/inventoryPrice';
import {
  buildStockModelSpecLines,
  displayScreenHint,
  orderStockCardSpecLines,
  stockAvailabilityLabel,
  type StockModelSpecLine,
} from '../../lib/stockModelCard';
import { ProductImageService } from '../../services/images/ProductImageService';

const COLLAPSED_SPEC_COUNT = 8;

interface StockModelCardProps {
  row: ModelInventoryRow;
  showPrice?: boolean;
  onSelect: () => void;
}

function formatSpecBullet(line: StockModelSpecLine): string {
  const value = line.value.trim();
  const label = line.label.trim();
  if (!label) return value;
  if (label.toLowerCase() === 'operating system') {
    return `OS: ${value}`;
  }
  if (value.toLowerCase().startsWith(label.toLowerCase())) return value;
  return `${label}: ${value}`;
}

export function StockModelCard({
  row,
  showPrice = false,
  onSelect,
}: StockModelCardProps): JSX.Element {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);
  const [specsExpanded, setSpecsExpanded] = useState(false);
  const specLines = useMemo(
    () => orderStockCardSpecLines(buildStockModelSpecLines(row.model)),
    [row.model],
  );
  const inStock = row.availableUnits > 0;
  const screenHint = displayScreenHint(row.model.display);
  const visibleSpecs = specsExpanded
    ? specLines
    : specLines.slice(0, COLLAPSED_SPEC_COUNT);
  const hasMoreSpecs = specLines.length > COLLAPSED_SPEC_COUNT;

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
          <span className={`stock-model-card__status ${inStock ? 'stock-model-card__status--in' : 'stock-model-card__status--out'}`}>
            {inStock ? 'In stock' : 'Out of stock'}
          </span>
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
              <Laptop size={52} strokeWidth={1.1} />
            </div>
          )}
        </div>

        <div className="stock-model-card__content">
          {row.model.color_options && (
            <p className="stock-model-card__colors">{row.model.color_options}</p>
          )}

          <header className="stock-model-card__header">
            {screenHint && (
              <p className="stock-model-card__screen-hint">{screenHint}</p>
            )}
            <h3 className="stock-model-card__title">{row.model.model_name}</h3>
            <p className="stock-model-card__number col-mono">{row.model.model_number}</p>
          </header>

          {showPrice && (
            <div className="stock-model-card__price-block">
              <p className="stock-model-card__price-label">Selling price</p>
              <p className="stock-model-card__price">
                {formatInventoryPrice(row.model.selling_price)}
              </p>
            </div>
          )}

          {specLines.length > 0 && (
            <div className="stock-model-card__specs">
              <ul className="stock-model-card__spec-list">
                {visibleSpecs.map((line) => (
                  <li key={`${line.label}-${line.value}`} className="stock-model-card__spec-item">
                    <span className="stock-model-card__spec-bullet" aria-hidden />
                    <span>{formatSpecBullet(line)}</span>
                  </li>
                ))}
              </ul>
              {hasMoreSpecs && (
                <button
                  type="button"
                  className="stock-model-card__spec-toggle"
                  onClick={(event) => {
                    event.stopPropagation();
                    setSpecsExpanded((current) => !current);
                  }}
                >
                  {specsExpanded ? (
                    <>
                      See less
                      <ChevronUp size={14} aria-hidden />
                    </>
                  ) : (
                    <>
                      See more
                      <ChevronDown size={14} aria-hidden />
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          <div className="stock-model-card__footer">
            <span className="stock-model-card__availability">
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
