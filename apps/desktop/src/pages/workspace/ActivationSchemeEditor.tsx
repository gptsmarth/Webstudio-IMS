import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { parseApiError } from '../../lib/apiError';
import {
  AsusActivationService,
  type ActivationScheme,
  type RateDecision,
  type SchemeChange,
  type SchemeEditMode,
  type SchemeEditPreview,
  type SchemeImport,
} from '../../services/api/AsusActivationService';

const changeLabels: Record<SchemeChange['mode'], string> = {
  upload: 'Original upload',
  dates: 'Dates corrected',
  replace: 'Workbook replaced',
  supplement: 'Workbook added',
  model_cn: 'Model CN corrected',
};

export function ActivationDialog({
  title,
  children,
  busy,
  onClose,
  wide = false,
  side = false,
}: {
  title: string;
  children: ReactNode;
  busy: boolean;
  onClose: () => void;
  wide?: boolean;
  side?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={
        'card activation__dialog' +
        (side ? ' activation__dialog--side' : wide ? ' activation__dialog--wide' : '')
      }
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className={side ? 'activation__drawer-header' : undefined}>
        <h2 id={titleId}>{title}</h2>
        {side && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={busy}>
            Close
          </button>
        )}
      </div>
      {children}
    </dialog>
  );
}

export function ActivationHistory({
  schemes,
  activeId,
  onManage,
}: {
  schemes: ActivationScheme[];
  activeId?: string;
  onManage?: (scheme: ActivationScheme) => void;
}) {
  return (
    <section className="activation__panel" aria-label="Activation scheme history">
      {!schemes.length && <p>Uploaded schemes will appear here.</p>}
      {[...schemes].reverse().map((scheme) => (
        <div className="activation__history-row" key={scheme.id}>
          <div className="activation__toolbar">
            <div>
              <strong>
                {scheme.date_from} to {scheme.date_to}
              </strong>
              <p>
                {scheme.filename} · {scheme.rule_count} model rates
              </p>
            </div>
            <div className="activation__actions">
              <span className="activation__badge">
                {scheme.id === activeId
                  ? 'Active'
                  : scheme.editable
                    ? 'Editable period'
                    : 'Archived'}
              </span>
              {onManage && scheme.editable && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onManage(scheme)}
                >
                  Manage scheme
                </button>
              )}
            </div>
          </div>
          <details>
            <summary>Workbook and edit history</summary>
            <ul>
              {(scheme.history ?? [])
                .slice()
                .reverse()
                .map((change, index) => (
                  <li key={change.changed_at + index}>
                    <strong>{changeLabels[change.mode]}</strong> · {change.filename} ·{' '}
                    {change.date_from} to {change.date_to}
                    {change.model && (
                      <span>
                        {' '}
                        · {change.model} · ₹{change.amount}
                        {change.note && ' · ' + change.note}
                      </span>
                    )}
                    {change.choices && (
                      <ul>
                        {Object.entries(change.choices).map(([model, choice]) => (
                          <li key={model}>
                            {model} ·{' '}
                            {choice.use === 'existing'
                              ? 'Kept existing rates'
                              : choice.date_from
                                ? 'Incoming rate from ' + choice.date_from + ' to ' + choice.date_to
                                : 'Incoming rate for full scheme'}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
            </ul>
          </details>
        </div>
      ))}
    </section>
  );
}

type Choice = 'existing' | 'full' | 'custom';
type ChoiceInput = { choice: Choice; from: string; to: string };
type Rate = SchemeEditPreview['conflicts'][number]['incoming'];

function RateValues({ rate }: { rate: Rate }) {
  const entries = [
    ['NOV T2 DBP', rate.dbp],
    ['Supported SRP', rate.srp],
    ['Supported DBP', rate.supported_dbp],
    ['Support on SRP', rate.support_on_srp],
    ['CN/Unit', rate.cn],
  ];
  return (
    <dl className="activation__rate-values">
      {entries.map(([label, amount]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {amount == null
              ? '—'
              : '₹' + Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ActivationSchemeEditor({
  scheme,
  onClose,
  onApplied,
}: {
  scheme: ActivationScheme;
  onClose: () => void;
  onApplied: (scheme: SchemeImport) => void;
}) {
  const [mode, setMode] = useState<SchemeEditMode>('dates');
  const [start, setStart] = useState(scheme.date_from);
  const [end, setEnd] = useState(scheme.date_to);
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<SchemeEditPreview>();
  const [choices, setChoices] = useState<Record<string, ChoiceInput>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const first = mode === 'supplement' ? scheme.date_from : start;
  const last = mode === 'supplement' ? scheme.date_to : end;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !first || !last || first > last || (mode !== 'dates' && !file)) return;
    setBusy(true);
    setError('');
    try {
      const workbook = mode === 'dates' ? undefined : file;
      if (!preview) {
        setChoices({});
        setPreview(
          await AsusActivationService.editScheme<SchemeEditPreview>(
            scheme.id,
            mode,
            first,
            last,
            workbook,
          ),
        );
      } else {
        const decisions: Record<string, RateDecision> = {};
        for (const { model } of preview.conflicts) {
          const choice = choices[model];
          if (!choice) return;
          decisions[model] =
            choice.choice === 'custom'
              ? { use: 'incoming', date_from: choice.from, date_to: choice.to }
              : { use: choice.choice === 'existing' ? 'existing' : 'incoming' };
        }
        onApplied(
          await AsusActivationService.editScheme<SchemeImport>(
            scheme.id,
            mode,
            first,
            last,
            workbook,
            preview.preview_id,
            decisions,
          ),
        );
      }
    } catch (err) {
      setError(parseApiError(err, 'Could not update the activation scheme.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ActivationDialog title="Manage activation scheme" busy={busy} onClose={onClose} wide>
      <form className="activation__panel" onSubmit={(event) => void submit(event)}>
        <p>
          {scheme.filename} · {scheme.date_from} to {scheme.date_to}
        </p>
        {error && (
          <p className="alert alert-danger" role="alert">
            {error}
          </p>
        )}
        {!preview ? (
          <>
            <label>
              <span className="form-label">Change to make</span>
              <select
                className="input"
                value={mode}
                disabled={busy}
                onChange={(event) => setMode(event.target.value as SchemeEditMode)}
              >
                <option value="dates">Edit dates</option>
                <option value="replace">Replace the workbook</option>
                <option value="supplement">Add another workbook</option>
              </select>
            </label>
            {mode === 'replace' && (
              <p>
                The replacement supplies all rates for this period. Earlier supplemental rates are
                superseded.
              </p>
            )}
            {mode === 'supplement' && (
              <p>
                Review any differences before choosing which rates apply within the scheme dates.
              </p>
            )}
            <fieldset className="activation__fields" disabled={busy}>
              {mode !== 'supplement' && (
                <>
                  <label>
                    <span className="form-label">From date</span>
                    <input
                      className="input"
                      type="date"
                      required
                      value={start}
                      onChange={(event) => setStart(event.target.value)}
                    />
                  </label>
                  <label>
                    <span className="form-label">To date</span>
                    <input
                      className="input"
                      type="date"
                      required
                      min={start}
                      value={end}
                      onChange={(event) => setEnd(event.target.value)}
                    />
                  </label>
                </>
              )}
              {mode !== 'dates' && (
                <label>
                  <span className="form-label">Activation workbook</span>
                  <input
                    type="file"
                    accept=".xlsx"
                    aria-label="Activation workbook to apply"
                    required={!file}
                    onChange={(event) => setFile(event.target.files?.[0])}
                  />
                  {file && <small>{file.name}</small>}
                </label>
              )}
            </fieldset>
          </>
        ) : (
          <>
            <p>
              Preview for {first} to {last}
              {file && mode !== 'dates' ? ' · ' + file.name : ''}.
            </p>
            <p>
              {mode === 'supplement'
                ? preview.added_rate_count +
                  ' model rates can be added and ' +
                  preview.conflicts.length +
                  ' require a choice.'
                : preview.model_count +
                  ' model rates will apply. Claims will be recalculated from their invoice dates.'}
            </p>
            {preview.conflicts.map(({ model, existing, incoming }) => {
              const decision = choices[model];
              return (
                <section
                  className="activation__conflict"
                  key={model}
                  aria-label={'Rate conflict for ' + model}
                >
                  <h3>{model}</h3>
                  <div className="activation__fields">
                    <div>
                      <strong>Existing rates</strong>
                      {existing.map(({ date_from, date_to, rate }) => (
                        <div key={date_from}>
                          <small>
                            {date_from} to {date_to}
                            {rate.filename ? ' · ' + rate.filename : ''}
                          </small>
                          <RateValues rate={rate} />
                        </div>
                      ))}
                    </div>
                    <div>
                      <strong>New workbook</strong>
                      <RateValues rate={incoming} />
                    </div>
                  </div>
                  <label>
                    <span className="form-label">Rate to apply for {model}</span>
                    <select
                      className="input"
                      required
                      disabled={busy}
                      value={decision?.choice ?? ''}
                      onChange={(event) => {
                        const choice = event.target.value as Choice | '';
                        setChoices((current) => {
                          const next = { ...current };
                          if (choice) next[model] = { choice, from: first, to: last };
                          else delete next[model];
                          return next;
                        });
                      }}
                    >
                      <option value="">Choose a rate</option>
                      <option value="existing">Keep existing rates</option>
                      <option value="full">New rate for full scheme</option>
                      <option value="custom">New rate for custom dates</option>
                    </select>
                  </label>
                  {decision?.choice === 'custom' && (
                    <fieldset className="activation__fields" disabled={busy}>
                      <label>
                        <span className="form-label">Apply new rate from</span>
                        <input
                          className="input"
                          type="date"
                          required
                          min={first}
                          max={last}
                          value={decision.from}
                          onChange={(event) =>
                            setChoices({
                              ...choices,
                              [model]: { ...decision, from: event.target.value },
                            })
                          }
                        />
                      </label>
                      <label>
                        <span className="form-label">Apply new rate through</span>
                        <input
                          className="input"
                          type="date"
                          required
                          min={decision.from || first}
                          max={last}
                          value={decision.to}
                          onChange={(event) =>
                            setChoices({
                              ...choices,
                              [model]: { ...decision, to: event.target.value },
                            })
                          }
                        />
                      </label>
                    </fieldset>
                  )}
                </section>
              );
            })}
            <p>
              Recorded payments keep their received amounts. Any variance is checked again against
              the updated expected CN.
            </p>
          </>
        )}
        <div className="activation__dialog-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          {preview && (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => {
                setPreview(undefined);
                setError('');
              }}
            >
              Back to edit
            </button>
          )}
          <button
            className="btn btn-primary"
            type="submit"
            disabled={
              busy || Boolean(preview && preview.conflicts.some(({ model }) => !choices[model]))
            }
          >
            {busy ? 'Working…' : preview ? 'Apply scheme changes' : 'Preview changes'}
          </button>
        </div>
      </form>
    </ActivationDialog>
  );
}
