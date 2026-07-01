import 'dart:typed_data';

class DownloadedFile {
  const DownloadedFile({
    required this.bytes,
    required this.filename,
    this.mimeType,
  });

  final Uint8List bytes;
  final String filename;
  final String? mimeType;
}
