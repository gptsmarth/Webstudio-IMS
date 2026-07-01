---
Title: Milestone 10F — Mobile Device Integration
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10E_REPORTS_ADMIN_REPORT.md
---

# Milestone 10F — Mobile Device Integration

## Summary

Milestone 10F adds native mobile device capabilities to the Flutter client: barcode scanning enhancements, camera product images, file import/export/share, push notification architecture, and future-ready scan input stubs. All features consume the same backend APIs as desktop — no duplicated business logic.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Barcode — serial number | ✅ | `BarcodeFieldResolver` + inventory scan workflow |
| Barcode — model number | ✅ | EAN-13 / model-pattern heuristics |
| Barcode — part number | ✅ | EAN-8 / Code39 manufacturer patterns |
| Barcode — manufacturer formats | ✅ | Code128, Code39, Codabar, EAN, UPC, ITF, Data Matrix |
| Camera — capture product image | ✅ | `ProductImageActions.captureFromCamera()` |
| Camera — upload image | ✅ | `POST /api/v1/product-images/upload` |
| Camera — preview image | ✅ | `ProductImagePreview` via proxy URL |
| File — import XML / backups | ✅ | `BackupScreen` → `POST /api/v1/settings/backups/import` |
| File — upload backups | ✅ | Multipart upload via `ApiClient.postMultipart` |
| File — download reports | ✅ | `GET /api/v1/reports/export` → save to documents |
| File — share reports | ✅ | `share_plus` via `FileTransferService` |
| Notifications — push architecture | ✅ | `PushNotificationService` + local channel |
| Notifications — background support | ✅ | `BackgroundNotificationCoordinator` on unread delta |
| Future — QR architecture | ✅ | `QrScanInputSource` stub in `scan_input_architecture.dart` |
| Future — NFC architecture | ✅ | `NfcScanInputSource` stub |
| Future — Bluetooth scanner | ✅ | `BluetoothScannerInputSource` stub |
| Permissions — camera | ✅ | `DevicePermissions` + platform manifests |
| Permissions — storage | ✅ | Photos / file picker gating |
| Permissions — notifications | ✅ | Settings screen + notifications screen init |
| Tests | ✅ | File transfer, scan architecture, barcode resolver (26 total) |

---

## Barcode scanner

Built on `mobile_scanner` (10C) with expanded format support and field detection feedback.

**Supported formats:** Code 128, Code 39, Codabar, EAN-8/13, UPC-A/E, ITF, Data Matrix, QR (inventory JSON payloads).

**Field resolution** (`barcode_field_resolver.dart`):

| Input pattern | Target field |
|---------------|--------------|
| Desktop inventory QR JSON | Serial number (+ optional inventory ID) |
| EAN-13 / UPC | Model number |
| EAN-8 | Part number |
| Alphanumeric model pattern | Model number |
| Manufacturer Code39 (e.g. `ABC-123456`) | Part number |
| Default | Serial number |

Scan result shows a snackbar with the detected field label before applying search filters.

**Future-ready:** `ScanInputRegistry` separates camera (implemented) from QR/NFC/Bluetooth (planned stubs).

---

## Camera & product images

| Step | API / module |
|------|--------------|
| Capture / gallery pick | `image_picker` + `DevicePermissions` |
| Upload | `POST /api/v1/product-images/upload` (`product_model_id` + file) |
| Preview | `GET /api/v1/product-images/proxy?url=…` |

Entry point: catalogue **Models** tab → camera icon → `showProductImageSheet()`.

---

## File support

### Backup import

`BackupScreen` → file picker (`.xml`, `.tar`, `.gz`, `.tgz`, `.zip`) → `SettingsRepository.importBackupFile()` → same endpoint as desktop `SettingsService.importBackup()`.

### Report export

`ReportsScreen` → export menu (XLSX / PDF) → `ReportRepository.exportReport()` → save or share via `FileTransferService`.

`ApiClient.downloadBytes()` handles binary responses and `Content-Disposition` filenames.

---

## Notifications

| Component | Role |
|-----------|------|
| `LocalPushNotificationService` | Android channel + iOS permission plumbing |
| `BackgroundNotificationCoordinator` | Surfaces local alerts when unread count increases after baseline |
| Bootstrap | Initializes notification plugin at app start |

Remote FCM/APNs token registration is deferred; architecture supports swapping in a remote adapter behind `PushNotificationService`.

---

## Permissions

| Permission | Android | iOS | UI |
|------------|---------|-----|-----|
| Camera | `CAMERA` | `NSCameraUsageDescription` | Before scan / capture |
| Storage / photos | `READ_MEDIA_IMAGES`, legacy read | `NSPhotoLibraryUsageDescription` | Gallery pick, backup import |
| Notifications | `POST_NOTIFICATIONS` | Local notification request | Settings + Notifications screen |

**Settings → Device permissions** shows grant status and request buttons for each kind.

---

## New modules

```
lib/core/device/
  device_permissions.dart
  file_transfer_service.dart
  push_notification_service.dart
  scan_input_architecture.dart
lib/features/media/
  data/product_image_repository.dart
  presentation/product_image_sheet.dart
lib/shared/models/downloaded_file.dart
```

**Dependencies added:** `file_picker`, `share_plus`, `path_provider`, `permission_handler`, `flutter_local_notifications`.

---

## API parity (desktop)

| Feature | Endpoint |
|---------|----------|
| Product image upload | `POST /api/v1/product-images/upload` |
| Product image proxy | `GET /api/v1/product-images/proxy` |
| Backup import | `POST /api/v1/settings/backups/import` |
| Report export | `GET /api/v1/reports/export` |

---

## Tests

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
```

| Test file | Coverage |
|-----------|----------|
| `file_transfer_test.dart` | Content-Disposition parsing, export extensions |
| `scan_input_architecture_test.dart` | Registry implemented vs planned sources |
| `barcode_field_resolver_test.dart` | QR, EAN, manufacturer part numbers, labels |

---

## Deferred / out of scope

- Remote push (FCM/APNs) token lifecycle and deep links
- Full NFC / Bluetooth HID scanner implementations
- Dedicated QR workflows beyond inventory JSON payloads
- Tally XML import (uses backup import endpoint for archive/XML backup files only)

---

## Ready for review

Milestone 10F is complete pending review. Next milestone can focus on offline sync, performance, or production hardening per product roadmap.
