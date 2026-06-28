import { useMemo } from 'react';
import { Printer, X } from 'lucide-react';
import {
  buildInventoryQrPayload,
  inventoryQrDataUrl,
  serializeInventoryQrPayload,
} from '../../lib/inventoryQr';

interface InventoryQrDialogProps {
  open: boolean;
  serialNumber: string;
  inventoryId: string;
  onClose: () => void;
}

export function InventoryQrDialog({
  open,
  serialNumber,
  inventoryId,
  onClose,
}: InventoryQrDialogProps): JSX.Element | null {
  const payload = useMemo(
    () => serializeInventoryQrPayload(buildInventoryQrPayload(inventoryId, serialNumber)),
    [inventoryId, serialNumber],
  );
  const imageUrl = useMemo(
    () => inventoryQrDataUrl(serialNumber, inventoryId, 200),
    [inventoryId, serialNumber],
  );

  if (!open) return null;

  const printLabel = () => {
    const win = window.open('', '_blank', 'width=320,height=420');
    if (!win) return;
    win.document.write(`
      <html><head><title>QR ${serialNumber}</title></head><body style="font-family:sans-serif;text-align:center;padding:24px;">
        <img src="${imageUrl}" alt="QR code" width="200" height="200" />
        <p style="font-family:monospace;font-size:14px;margin-top:12px;">${serialNumber}</p>
      </body></html>
    `);
    win.document.close();
    win.print();
  };

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="inv-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="inv-dialog__header">
          <h2 className="inv-dialog__title">Inventory QR</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>
        <div className="inv-dialog__body inv-qr-dialog">
          <img src={imageUrl} alt={`QR code for ${serialNumber}`} className="inv-qr-dialog__image" />
          <p className="inv-qr-dialog__serial col-mono">{serialNumber}</p>
          <p className="inv-qr-dialog__hint">Payload prepared for future mobile scanner compatibility.</p>
          <code className="inv-qr-dialog__payload col-mono">{payload}</code>
        </div>
        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
          <button type="button" className="btn btn-primary btn-sm" onClick={printLabel}>
            <Printer size={14} aria-hidden />
            Print label
          </button>
        </footer>
      </div>
    </div>
  );
}
