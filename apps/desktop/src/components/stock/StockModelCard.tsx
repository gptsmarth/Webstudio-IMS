import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, Laptop } from 'lucide-react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import {
  buildStockModelSpecLines,
  displayScreenHint,
  orderStockCardSpecLines,
  stockAvailabilityLabel,
  type StockModelSpecLine,
} from '../../lib/stockModelCard';
import { useProductImage } from '../../hooks/useProductImage';
import { formatRelativeTime } from '../../lib/datetime';

const COLLAPSED_SPEC_COUNT = 6;

interface StockModelCardProps {
  row: ModelInventoryRow;
  showPrice?: boolean;
  showLivePrice?: boolean;
  onSelect: () => void;
}

function formatSpecBullet(line: StockModelSpecLine): string {
  const value = line.value.trim();
  const label = line.label.trim();
  if (!label) return value;
  if (label.toLowerCase() === 'operating system') {
    return `${value}`;
  }
  if (value.toLowerCase().startsWith(label.toLowerCase())) return value;
  return `${label}: ${value}`;
}

function formatCardPrice(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === '' || Number(val) === 0)
    return 'Price on request';
  const num = typeof val === 'string' ? Number(val) : val;
  if (Number.isNaN(num) || num === 0) return 'Price on request';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
    .format(num)
    .replace('₹', '₹ ');
}

export function StockModelCard({
  row,
  showPrice = false,
  showLivePrice = false,
  onSelect,
}: StockModelCardProps): JSX.Element {
  const [specsExpanded, setSpecsExpanded] = useState(false);
  const [imageBroken, setImageBroken] = useState(false);
  const image = useProductImage(row.model.id, {
    remoteUrl: row.model.product_image_url,
    brandName: row.model.brand_name,
    modelName: row.model.model_name,
  });
  const specLines = useMemo(
    () => orderStockCardSpecLines(buildStockModelSpecLines(row.model)),
    [row.model],
  );
  const screenHint = displayScreenHint(row.model.display);
  const visibleSpecs = specsExpanded ? specLines : specLines.slice(0, COLLAPSED_SPEC_COUNT);
  const hasMoreSpecs = specLines.length > COLLAPSED_SPEC_COUNT;
  const showImage = !image.loading && !image.failed && !imageBroken;

  useEffect(() => {
    setImageBroken(false);
  }, [image.src]);

  return (
    <article className="stock-model-card">
      <button type="button" className="stock-model-card__main" onClick={onSelect}>
        <div className="stock-model-card__top-bar">
          <div />
          <span className="stock-model-card__stock-count">
            {stockAvailabilityLabel(row.availableUnits)}
          </span>
        </div>

        <div className="stock-model-card__media">
          {image.loading ? (
            <div className="stock-model-card__image stock-model-card__image--placeholder skeleton" />
          ) : showImage ? (
            <img
              src={image.src}
              alt={row.model.model_name}
              className="stock-model-card__image"
              loading="lazy"
              onError={() => setImageBroken(true)}
            />
          ) : (
            <div
              className="stock-model-card__image stock-model-card__image--placeholder"
              aria-hidden
            >
              <Laptop size={64} strokeWidth={1} />
            </div>
          )}
        </div>

        <div className="stock-model-card__content">
          <header className="stock-model-card__header">
            {screenHint && <p className="stock-model-card__screen-hint">{screenHint}</p>}
            <h3 className="stock-model-card__title">{row.model.model_name}</h3>
            <p className="stock-model-card__number col-mono">{row.model.model_number}</p>
          </header>

          <hr className="stock-model-card__divider" />

          {showPrice && (
            <>
              <div className="stock-model-card__price-block">
                <p
                  className="stock-model-card__price"
                  style={
                    !row.model.selling_price || Number(row.model.selling_price) === 0
                      ? {
                          fontSize: '18px',
                          fontWeight: 600,
                          color: 'var(--color-text-secondary)',
                          letterSpacing: 'normal',
                        }
                      : undefined
                  }
                >
                  {formatCardPrice(row.model.selling_price)}
                </p>
              </div>
              <hr className="stock-model-card__divider" />
            </>
          )}

          {showLivePrice &&
            row.model.brand_name?.trim().toUpperCase() === 'ASUS' &&
            row.model.category !== 'accessory' && (
              <>
                <div className="stock-model-card__price-block">
                  <p style={{ fontSize: 13, color: 'var(--color-text-tertiary)', margin: 0 }}>
                    ASUS Price:{' '}
                    <strong style={{ color: 'var(--color-text-primary)' }}>
                      {row.model.live_price ? formatCardPrice(row.model.live_price) : 'NA'}
                    </strong>
                  </p>
                  {row.model.live_price_updated_at && (
                    <p
                      style={{
                        fontSize: 11,
                        color: 'var(--color-text-tertiary)',
                        margin: '2px 0 0',
                      }}
                      title={row.model.live_price_source_url ?? undefined}
                    >
                      as of {formatRelativeTime(row.model.live_price_updated_at)}
                    </p>
                  )}
                </div>
                <hr className="stock-model-card__divider" />
              </>
            )}

          {specLines.length > 0 && (
            <div className="stock-model-card__specs">
              <ul className="stock-model-card__spec-list">
                {visibleSpecs.map((line) => (
                  <li key={`${line.label}-${line.value}`} className="stock-model-card__spec-item">
                    <span className="stock-model-card__spec-bullet" aria-hidden>
                      •
                    </span>
                    <span className="stock-model-card__spec-text">{formatSpecBullet(line)}</span>
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
            <span className="stock-model-card__cta">
              View units & details
              <ArrowRight size={14} aria-hidden />
            </span>
          </div>
        </div>
      </button>
    </article>
  );
}
