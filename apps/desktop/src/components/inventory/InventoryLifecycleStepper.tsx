import type { LifecycleStep } from '../../lib/inventoryLifecycle';

interface InventoryLifecycleStepperProps {
  steps: LifecycleStep[];
}

export function InventoryLifecycleStepper({ steps }: InventoryLifecycleStepperProps): JSX.Element {
  return (
    <ol className="inv-lifecycle" aria-label="Inventory lifecycle">
      {steps.map((step, index) => (
        <li
          key={step.id}
          className={
            [
              'inv-lifecycle__step',
              step.complete ? 'inv-lifecycle__step--complete' : '',
              step.current ? 'inv-lifecycle__step--current' : '',
            ]
              .filter(Boolean)
              .join(' ') || undefined
          }
        >
          <span className="inv-lifecycle__marker" aria-hidden />
          <div className="inv-lifecycle__content">
            <span className="inv-lifecycle__label">{step.label}</span>
            {step.detail && <span className="inv-lifecycle__detail">{step.detail}</span>}
          </div>
          {index < steps.length - 1 && <span className="inv-lifecycle__connector" aria-hidden />}
        </li>
      ))}
    </ol>
  );
}
