import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, Monitor, Plus } from 'lucide-react';
import { ComparisonTable } from '../../components/comparison/ComparisonTable';
import { PageContainer, PageHeader } from '../../components/shell/TopToolbar';
import {
  addComparisonSlot,
  initialComparisonSlots,
  MAX_COMPARISON_LAPTOPS,
  removeComparisonSlot,
  setComparisonLaptop,
  type ComparisonSlot,
} from '../../lib/laptopComparison';
import { useStockNavStore } from '../../store/useHierarchyNavStore';

function CustomerView({
  slots,
  showSellingPrice,
  onClose,
}: {
  slots: ComparisonSlot[];
  showSellingPrice: boolean;
  onClose: () => void;
}): JSX.Element {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return createPortal(
    <dialog
      ref={dialog}
      className="comparison-presentation"
      aria-labelledby="comparison-presentation-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header className="comparison-presentation__header">
        <h1 id="comparison-presentation-title">Laptop comparison</h1>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
          <ArrowLeft size={16} aria-hidden />
          Back to editing
        </button>
      </header>
      <ComparisonTable slots={slots} customer showSellingPrice={showSellingPrice} />
    </dialog>,
    document.body,
  );
}

export function ComparisonPage(): JSX.Element {
  const [slots, setSlots] = useState(initialComparisonSlots);
  const [presenting, setPresenting] = useState(false);
  const stockPricePreference = useStockNavStore((state) => state.showSellingPrice);
  const [showPrice, setShowPrice] = useState(stockPricePreference);
  const nextId = useRef(3);
  const customerSlots = slots.filter((slot) => slot.laptop);

  return (
    <PageContainer>
      <PageHeader
        title="Comparison"
        actions={
          <>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={slots.length >= MAX_COMPARISON_LAPTOPS}
              onClick={() => {
                const id = nextId.current++;
                setSlots((current) => addComparisonSlot(current, id));
              }}
            >
              <Plus size={17} aria-hidden />
              Add Laptop
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={customerSlots.length < 2}
              onClick={() => setPresenting(true)}
            >
              <Monitor size={17} aria-hidden />
              Customer View
            </button>
          </>
        }
      />
      <div className="comparison-options">
        <label>
          <input
            type="checkbox"
            checked={showPrice}
            onChange={(event) => setShowPrice(event.target.checked)}
          />
          Show selling price
        </label>
        {customerSlots.length < 2 && <span>Select two laptops to open Customer View.</span>}
      </div>
      <div hidden={presenting}>
        <ComparisonTable
          slots={slots}
          showSellingPrice={showPrice}
          onSelect={(id, laptop) => setSlots((current) => setComparisonLaptop(current, id, laptop))}
          onRemove={(id) => setSlots((current) => removeComparisonSlot(current, id))}
        />
      </div>
      {presenting && (
        <CustomerView
          slots={customerSlots}
          showSellingPrice={showPrice}
          onClose={() => setPresenting(false)}
        />
      )}
    </PageContainer>
  );
}
