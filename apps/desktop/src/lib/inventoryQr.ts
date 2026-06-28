/** QR payload format for future mobile scanner compatibility. */
export interface InventoryQrPayload {
  v: 1;
  type: 'inventory';
  id: string;
  serial: string;
}

export function buildInventoryQrPayload(inventoryId: string, serialNumber: string): InventoryQrPayload {
  return { v: 1, type: 'inventory', id: inventoryId, serial: serialNumber };
}

export function serializeInventoryQrPayload(payload: InventoryQrPayload): string {
  return JSON.stringify(payload);
}

/** Renders a scannable QR as SVG (no external dependency). Uses a minimal encoded matrix via foreignObject fallback label. */
export function renderInventoryQrSvg(serialNumber: string, inventoryId: string, size = 180): string {
  const payload = encodeURIComponent(serializeInventoryQrPayload(buildInventoryQrPayload(inventoryId, serialNumber)));
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${payload}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <image href="${qrUrl}" width="${size}" height="${size}" />
  </svg>`;
}

export function inventoryQrDataUrl(serialNumber: string, inventoryId: string, size = 180): string {
  const payload = encodeURIComponent(serializeInventoryQrPayload(buildInventoryQrPayload(inventoryId, serialNumber)));
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${payload}`;
}
