import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';

enum DevicePermissionKind { camera, storage, notifications }

class PermissionRequestOutcome {
  const PermissionRequestOutcome({
    required this.granted,
    this.permanentlyDenied = false,
  });

  final bool granted;
  final bool permanentlyDenied;
}

class DevicePermissions {
  const DevicePermissions();

  Future<bool> ensure(DevicePermissionKind kind) async {
    final outcome = await _request(kind);
    return outcome.granted;
  }

  Future<PermissionRequestOutcome> requestWithContext(
    BuildContext context,
    DevicePermissionKind kind,
  ) async {
    final permission = _map(kind);
    var status = await permission.status;
    if (status.isGranted || status.isLimited) {
      return const PermissionRequestOutcome(granted: true);
    }

    if (status.isPermanentlyDenied) {
      await _showSettingsDialog(context, kind);
      return const PermissionRequestOutcome(granted: false, permanentlyDenied: true);
    }

    if (status.isDenied && context.mounted) {
      final proceed = await _showRationaleDialog(context, kind);
      if (!proceed || !context.mounted) {
        return const PermissionRequestOutcome(granted: false);
      }
    }

    final requested = await permission.request();
    if (requested.isGranted || requested.isLimited) {
      return const PermissionRequestOutcome(granted: true);
    }
    if (requested.isPermanentlyDenied) {
      if (context.mounted) {
        await _showSettingsDialog(context, kind);
      }
      return const PermissionRequestOutcome(granted: false, permanentlyDenied: true);
    }
    return const PermissionRequestOutcome(granted: false);
  }

  Future<PermissionRequestOutcome> _request(DevicePermissionKind kind) async {
    final permission = _map(kind);
    final status = await permission.status;
    if (status.isGranted || status.isLimited) {
      return const PermissionRequestOutcome(granted: true);
    }
    if (status.isPermanentlyDenied) {
      return const PermissionRequestOutcome(granted: false, permanentlyDenied: true);
    }
    if (status.isDenied) {
      final requested = await permission.request();
      return PermissionRequestOutcome(
        granted: requested.isGranted || requested.isLimited,
        permanentlyDenied: requested.isPermanentlyDenied,
      );
    }
    return const PermissionRequestOutcome(granted: false);
  }

  Future<bool> isGranted(DevicePermissionKind kind) async {
    final status = await _map(kind).status;
    return status.isGranted || status.isLimited;
  }

  Future<bool> _showRationaleDialog(BuildContext context, DevicePermissionKind kind) async {
    final copy = _copyFor(kind);
    final value = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(copy.title),
        content: Text(copy.rationale),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Not now')),
          FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Continue')),
        ],
      ),
    );
    return value ?? false;
  }

  Future<void> _showSettingsDialog(BuildContext context, DevicePermissionKind kind) {
    final copy = _copyFor(kind);
    return showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(copy.title),
        content: Text(copy.settingsMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              Navigator.pop(dialogContext);
              await openAppSettings();
            },
            child: const Text('Open settings'),
          ),
        ],
      ),
    );
  }

  _PermissionCopy _copyFor(DevicePermissionKind kind) => switch (kind) {
        DevicePermissionKind.camera => const _PermissionCopy(
            title: 'Camera access required',
            rationale:
                'WEBSTUDIO IMS uses the camera to scan inventory barcodes and capture product photos. '
                'Grant camera access to continue.',
            settingsMessage:
                'Camera access was denied. Open system settings and enable Camera for WEBSTUDIO IMS.',
          ),
        DevicePermissionKind.storage => const _PermissionCopy(
            title: 'Photo library access required',
            rationale:
                'WEBSTUDIO IMS needs photo library access so you can choose product images to upload.',
            settingsMessage:
                'Photo library access was denied. Open system settings and enable Photos for WEBSTUDIO IMS.',
          ),
        DevicePermissionKind.notifications => const _PermissionCopy(
            title: 'Notifications required',
            rationale:
                'WEBSTUDIO IMS sends operational alerts such as sync failures and inventory notifications.',
            settingsMessage:
                'Notifications were denied. Open system settings and enable Notifications for WEBSTUDIO IMS.',
          ),
      };

  Permission _map(DevicePermissionKind kind) => switch (kind) {
        DevicePermissionKind.camera => Permission.camera,
        DevicePermissionKind.storage => Permission.photos,
        DevicePermissionKind.notifications => Permission.notification,
      };
}

class _PermissionCopy {
  const _PermissionCopy({
    required this.title,
    required this.rationale,
    required this.settingsMessage,
  });

  final String title;
  final String rationale;
  final String settingsMessage;
}

final devicePermissionsProvider = Provider<DevicePermissions>((ref) => const DevicePermissions());
