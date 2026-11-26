import { useEffect, useState } from 'react';
import { LaptopMinimal, X } from 'lucide-react';
import { comparisonRows, type ComparisonSlot } from '../../lib/laptopComparison';
import { ComparisonService, type ComparisonLaptop } from '../../services/api/ComparisonService';
import { LaptopPicker } from './LaptopPicker';
import './comparison.css';

const priceFormat = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });

function LaptopPhoto({ laptop }: { laptop: ComparisonLaptop }): JSX.Element {
  const [managedSource, setManagedSource] = useState<string>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!laptop.managed_image || !laptop.model_id) return;
    let active = true;
    let imageUrl: string | undefined;
    void ComparisonService.savedImage(laptop.model_id)
      .then((blob) => {
        if (active) {
          imageUrl = URL.createObjectURL(blob);
          setManagedSource(imageUrl);
        }
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [laptop.managed_image, laptop.model_id]);

  const source = laptop.managed_image ? managedSource : laptop.image_url;
  if (!source || failed) {
    return (
      <figure className="comparison-laptop__photo comparison-laptop__photo--placeholder">
        <div className="comparison-laptop__photo-mark">
          <LaptopMinimal size={40} strokeWidth={1.4} aria-hidden />
        </div>
        <figcaption>
          {laptop.managed_image && !failed ? 'Loading photo…' : 'Photo unavailable'}
        </figcaption>
      </figure>
    );
  }
  return (
    <figure className="comparison-laptop__photo">
      <img
        src={source}
        alt={laptop.brand + ' ' + laptop.model_number}
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
      />
    </figure>
  );
}

interface ComparisonTableProps {
  slots: ComparisonSlot[];
  customer?: boolean;
  showSellingPrice?: boolean;
  onSelect?: (id: number, laptop: ComparisonLaptop | null) => void;
  onRemove?: (id: number) => void;
}

export function ComparisonTable({
  slots,
  customer = false,
  showSellingPrice = true,
  onSelect,
  onRemove,
}: ComparisonTableProps): JSX.Element {
  const hasModels = slots.some((slot) => slot.laptop);
  return (
    <div
      className="comparison-scroll"
      tabIndex={0}
      role="region"
      aria-label="Side-by-side laptop specifications"
    >
      <table
        className="comparison-table"
        aria-label="Laptop comparison"
        style={{ minWidth: 136 + slots.length * 242 }}
      >
        <colgroup>
          <col className="comparison-table__component-column" />
          {slots.map(({ id }) => (
            <col key={id} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th scope="col" className="comparison-table__component">
              Component
            </th>
            {slots.map(({ id, laptop }, index) => (
              <th key={id} scope="col" className="comparison-table__laptop">
                <div className="comparison-laptop">
                  {!customer && (
                    <div className="comparison-laptop__top">
                      <span>Laptop {index + 1}</span>
                      {id > 2 && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          aria-label={'Remove laptop ' + (index + 1)}
                          onClick={() => onRemove?.(id)}
                        >
                          <X size={16} aria-hidden />
                        </button>
                      )}
                    </div>
                  )}
                  {laptop ? (
                    <>
                      <LaptopPhoto
                        key={laptop.model_id ?? laptop.brand + '|' + laptop.model_number}
                        laptop={laptop}
                      />
                      <div className="comparison-laptop__identity">
                        <span className="comparison-laptop__brand">{laptop.brand}</span>
                        <h2>{laptop.model_name ?? laptop.model_number}</h2>
                        {laptop.model_name !== laptop.model_number && (
                          <span className="comparison-laptop__model">{laptop.model_number}</span>
                        )}
                        <div className="comparison-laptop__status">
                          <span className="comparison-laptop__source" data-source={laptop.source}>
                            {laptop.source === 'inventory' ? 'In Stock' : 'External Research'}
                          </span>
                          {laptop.source === 'inventory' && laptop.available_units !== null && (
                            <span>{laptop.available_units} available</span>
                          )}
                        </div>
                        {laptop.source === 'inventory' &&
                          showSellingPrice &&
                          Number(laptop.selling_price) > 0 && (
                            <span className="comparison-laptop__price">
                              {priceFormat.format(Number(laptop.selling_price))}
                            </span>
                          )}
                      </div>
                    </>
                  ) : (
                    <div className="comparison-laptop__empty">
                      <LaptopMinimal size={39} strokeWidth={1.35} aria-hidden />
                      <span>Choose a laptop</span>
                    </div>
                  )}
                  {!customer && onSelect && (
                    <LaptopPicker
                      index={index + 1}
                      laptop={laptop}
                      onSelect={(selected) => onSelect(id, selected)}
                    />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        {hasModels && (
          <tbody>
            {comparisonRows(slots, customer).map((row) => (
              <tr key={row.key} data-different={row.differs || undefined}>
                <th scope="row" className="comparison-table__component">
                  {row.heading}
                </th>
                {row.values.map((values, index) => (
                  <td
                    key={slots[index].id}
                    className={values.length ? undefined : 'comparison-table__missing'}
                  >
                    {values.length > 0
                      ? values.map((value) => <div key={value}>{value}</div>)
                      : 'Not available'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}
