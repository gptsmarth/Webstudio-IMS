import { structuredRowsFromObject, formatStructuredJson } from '../../lib/structuredData';

interface StructuredDataPanelProps {
  title: string;
  value: Record<string, unknown> | null;
  variant?: 'before' | 'after' | 'neutral';
  emptyLabel?: string;
}

export function StructuredDataPanel({
  title,
  value,
  variant = 'neutral',
  emptyLabel = 'No data recorded',
}: StructuredDataPanelProps): JSX.Element {
  const rows = structuredRowsFromObject(value);
  const json = formatStructuredJson(value);

  return (
    <div className={`struct-panel struct-panel--${variant}`}>
      <h4 className="struct-panel__title">{title}</h4>

      {rows.length === 0 ? (
        <p className="struct-panel__empty">{emptyLabel}</p>
      ) : (
        <dl className="struct-panel__rows">
          {rows.map((row) => (
            <div key={row.key} className="struct-panel__row">
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {value && Object.keys(value).length > 0 && (
        <details className="struct-panel__raw">
          <summary>View raw JSON</summary>
          <pre className="struct-panel__json">{json}</pre>
        </details>
      )}
    </div>
  );
}
