import 'package:mobile_scanner/mobile_scanner.dart';

import 'barcode_field_resolver.dart';

/// Picks the best barcode when multiple labels are visible (e.g. laptop box).
Barcode? selectBarcodeForTarget({
  required List<Barcode> barcodes,
  required BarcodeFieldTarget preferredTarget,
}) {
  if (barcodes.isEmpty) return null;

  final candidates = barcodes.where((barcode) {
    final raw = barcode.rawValue?.trim();
    return raw != null && raw.isNotEmpty;
  }).toList();

  if (candidates.isEmpty) return null;

  Barcode? best;
  var bestScore = -1;

  for (final barcode in candidates) {
    final raw = barcode.rawValue!.trim();
    final resolved = BarcodeFieldResolver.resolve(
      rawValue: raw,
      format: barcode.format.name,
      preferredTarget: preferredTarget,
    );
    final score = _scoreMatch(resolved.targetField, preferredTarget, raw);
    if (score > bestScore) {
      bestScore = score;
      best = barcode;
    }
  }

  return best;
}

int _scoreMatch(BarcodeFieldTarget resolved, BarcodeFieldTarget preferred, String raw) {
  var score = 0;
  if (resolved == preferred) score += 100;
  if (preferred == BarcodeFieldTarget.serialNumber &&
      BarcodeFieldResolver.looksLikeManufacturerSerial(raw)) {
    score += 50;
  }
  if (preferred == BarcodeFieldTarget.partNumber && BarcodeFieldResolver.looksLikePartNumber(raw)) {
    score += 40;
  }
  if (preferred == BarcodeFieldTarget.modelNumber && BarcodeFieldResolver.looksLikeModelNumber(raw)) {
    score += 40;
  }
  if (preferred == BarcodeFieldTarget.serialNumber) {
    score += raw.length.clamp(0, 24);
  }
  return score;
}
