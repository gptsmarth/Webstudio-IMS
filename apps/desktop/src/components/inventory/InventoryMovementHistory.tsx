import { extractMovementHistory, formatMovementTimestamp } from '../../lib/inventoryMovement';
import type { AuditLogEntry } from '../../services/api/AuditService';

interface InventoryMovementHistoryProps {
  auditLogs: AuditLogEntry[];
}

export function InventoryMovementHistory({
  auditLogs,
}: InventoryMovementHistoryProps): JSX.Element {
  const movements = extractMovementHistory(auditLogs);

  if (movements.length === 0) {
    return (
      <p className="inv-drawer__muted">No location transfers recorded for this serial number.</p>
    );
  }

  return (
    <div className="inv-movement-history">
      <ol className="inv-movement-history__list">
        {movements.map((move) => (
          <li key={move.id} className="inv-movement-history__item">
            <div className="inv-movement-history__route">
              <span>{move.fromLocation}</span>
              <span className="inv-movement-history__arrow" aria-hidden>
                →
              </span>
              <span>{move.toLocation}</span>
            </div>
            <span className="inv-movement-history__meta">
              {formatMovementTimestamp(move.movedAt)} · {move.actor}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
