import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';

enum DevicePermissionKind { camera, storage, notifications }

class DevicePermissions {
  const DevicePermissions();

  Future<bool> ensure(DevicePermissionKind kind) async {
    final permission = _map(kind);
    final status = await permission.status;
    if (status.isGranted) return true;
    if (status.isDenied || status.isLimited) {
      final requested = await permission.request();
      return requested.isGranted || requested.isLimited;
    }
    if (status.isPermanentlyDenied) return false;
    return false;
  }

  Future<bool> isGranted(DevicePermissionKind kind) async {
    final status = await _map(kind).status;
    return status.isGranted || status.isLimited;
  }

  Permission _map(DevicePermissionKind kind) => switch (kind) {
        DevicePermissionKind.camera => Permission.camera,
        DevicePermissionKind.storage => Permission.photos,
        DevicePermissionKind.notifications => Permission.notification,
      };
}

final devicePermissionsProvider = Provider<DevicePermissions>((ref) => const DevicePermissions());
