import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/inventory/domain/barcode_field_resolver.dart';
import '../../features/inventory/presentation/barcode_scanner_screen.dart';
import 'device_permissions.dart';

/// Opens the barcode scanner after a single camera permission flow.
Future<BarcodeScanResult?> openBarcodeScanner(
  BuildContext context,
  WidgetRef ref, {
  BarcodeFieldTarget preferredTarget = BarcodeFieldTarget.serialNumber,
}) async {
  final outcome = await ref
      .read(devicePermissionsProvider)
      .requestWithContext(context, DevicePermissionKind.camera);
  if (!outcome.granted || !context.mounted) return null;

  return Navigator.of(context).push<BarcodeScanResult>(
    MaterialPageRoute(
      builder: (_) => BarcodeScannerScreen(preferredTarget: preferredTarget),
    ),
  );
}
