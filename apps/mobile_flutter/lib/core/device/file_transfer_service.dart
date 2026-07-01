import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

class PickedDeviceFile {
  const PickedDeviceFile({
    required this.name,
    required this.bytes,
    this.path,
  });

  final String name;
  final Uint8List bytes;
  final String? path;
}

class SavedDeviceFile {
  const SavedDeviceFile({required this.path, required this.name});

  final String path;
  final String name;
}

class FileTransferService {
  Future<PickedDeviceFile?> pickFile({
    List<String>? allowedExtensions,
  }) async {
    final result = await FilePicker.platform.pickFiles(
      type: allowedExtensions == null ? FileType.any : FileType.custom,
      allowedExtensions: allowedExtensions,
      withData: true,
    );
    if (result == null || result.files.isEmpty) return null;
    final file = result.files.first;
    final bytes = file.bytes;
    if (bytes == null && file.path != null) {
      return PickedDeviceFile(
        name: file.name,
        bytes: await File(file.path!).readAsBytes(),
        path: file.path,
      );
    }
    if (bytes == null) return null;
    return PickedDeviceFile(name: file.name, bytes: bytes, path: file.path);
  }

  Future<SavedDeviceFile> saveToDocuments({
    required String filename,
    required Uint8List bytes,
  }) async {
    final directory = await getApplicationDocumentsDirectory();
    final path = '${directory.path}/$filename';
    final file = File(path);
    await file.writeAsBytes(bytes, flush: true);
    return SavedDeviceFile(path: path, name: filename);
  }

  Future<void> shareFile({
    required String filename,
    required Uint8List bytes,
    String? mimeType,
  }) async {
    final saved = await saveToDocuments(filename: filename, bytes: bytes);
    await Share.shareXFiles(
      [XFile(saved.path, mimeType: mimeType, name: filename)],
      subject: filename,
    );
  }
}

String parseContentDispositionFilename(String? header, String fallback) {
  if (header == null || header.isEmpty) return fallback;
  final match = RegExp(r'filename="?([^";]+)"?').firstMatch(header);
  return match?.group(1) ?? fallback;
}

String exportExtensionForFormat(String format) => switch (format.toLowerCase()) {
      'pdf' => 'pdf',
      _ => 'xlsx',
    };

final fileTransferServiceProvider = Provider<FileTransferService>((ref) => FileTransferService());
