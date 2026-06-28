import { Check } from 'lucide-react';

export interface SetupStep {
  number: number;
  label: string;
}

interface SetupStepperProps {
  steps: SetupStep[];
  currentStep: number;
}

export function SetupStepper({ steps, currentStep }: SetupStepperProps): JSX.Element {
  return (
    <ol className="setup-stepper" aria-label="Setup progress">
      {steps.map((step, index) => {
        const isComplete = currentStep > step.number;
        const isCurrent = currentStep === step.number;

        return (
          <li key={step.number} className="setup-stepper__item">
            <div className="setup-stepper__step">
              <div
                className={[
                  'setup-stepper__circle',
                  isComplete ? 'setup-stepper__circle--complete' : '',
                  isCurrent ? 'setup-stepper__circle--current' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                aria-current={isCurrent ? 'step' : undefined}
              >
                {isComplete ? <Check size={12} strokeWidth={2.5} aria-hidden="true" /> : step.number}
              </div>
              <span className={`setup-stepper__label ${isCurrent ? 'setup-stepper__label--current' : ''}`}>
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={[
                  'setup-stepper__connector',
                  isComplete ? 'setup-stepper__connector--complete' : '',
                  isCurrent ? 'setup-stepper__connector--active' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                aria-hidden="true"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
