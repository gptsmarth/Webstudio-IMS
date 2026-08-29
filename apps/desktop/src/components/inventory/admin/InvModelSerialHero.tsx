import { useEffect, useMemo, useState } from 'react';
import { Laptop } from 'lucide-react';
import type { ProductModel } from '../../../services/api/ProductModelService';
import { buildStockModelSpecLines } from '../../../lib/stockModelCard';
import { formatInventoryPrice } from '../../../lib/inventoryPrice';
import { useProductImage } from '../../../hooks/useProductImage';
import { InventoryBrandCell } from '../InventoryBrandCell';

interface InvModelSerialHeroProps {
  model: ProductModel;
  unitCount: number;
  availableCount: number;
  onEditModel?: () => void;
}

export function InvModelSerialHero({
  model,
  unitCount,
  availableCount,
  onEditModel,
}: InvModelSerialHeroProps): JSX.Element {
  const [imageBroken, setImageBroken] = useState(false);
  const image = useProductImage(model.id, {
    remoteUrl: model.product_image_url,
    brandName: model.brand_name,
    modelName: model.model_name,
  });
  const specLines = useMemo(() => buildStockModelSpecLines(model), [model]);
  const showImage = !image.loading && !image.failed && !imageBroken;

  useEffect(() => {
    setImageBroken(false);
  }, [image.src]);

  return (
    <section className="inv-model-hero" aria-label="Model overview">
      <div className="inv-model-hero__media">
        {showImage ? (
          <img
            src={image.src}
            alt={model.model_name}
            className="inv-model-hero__image"
            onError={() => setImageBroken(true)}
          />
        ) : (
          <div className="inv-model-hero__image inv-model-hero__image--placeholder" aria-hidden>
            <Laptop size={42} strokeWidth={1.25} />
          </div>
        )}
      </div>
      <div className="inv-model-hero__content">
        <div className="inv-model-hero__top-row">
          <p className="inv-model-hero__eyebrow">
            <InventoryBrandCell brandName={model.brand_name ?? ''} />
            {model.display && <span className="inv-model-hero__display">{model.display}</span>}
          </p>
          {onEditModel && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onEditModel}>
              Edit model
            </button>
          )}
        </div>
        <h2 className="inv-model-hero__title">{model.model_name}</h2>
        <p className="inv-model-hero__model-number col-mono">{model.model_number}</p>
        <div className="inv-model-hero__prices">
          <div>
            <span className="inv-model-hero__price-label">Selling price</span>
            <strong>{formatInventoryPrice(model.selling_price)}</strong>
          </div>
          <div>
            <span className="inv-model-hero__price-label">Purchase price</span>
            <strong>{formatInventoryPrice(model.purchase_price)}</strong>
          </div>
        </div>
        <p className="inv-model-hero__stats">
          <span>{availableCount} available</span>
          <span aria-hidden>·</span>
          <span>{unitCount} total units</span>
        </p>
        <ul className="inv-model-hero__spec-list">
          {specLines.map((line) => (
            <li key={line.label} className="inv-model-hero__spec-item">
              <span className="inv-model-hero__spec-bullet" aria-hidden />
              <span>
                <strong>{line.label}:</strong> {line.value}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
