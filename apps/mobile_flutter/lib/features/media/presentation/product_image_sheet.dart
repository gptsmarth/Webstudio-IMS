import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/device/device_permissions.dart';
import '../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../data/product_image_repository.dart';

class ProductImageActions {
  ProductImageActions(this._ref);

  final Ref _ref;
  final _picker = ImagePicker();

  Future<Uint8List?> captureFromCamera(BuildContext context) async {
    final permissions = _ref.read(devicePermissionsProvider);
    final outcome = await permissions.requestWithContext(context, DevicePermissionKind.camera);
    if (!outcome.granted) return null;
    final image = await _picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (image == null) return null;
    return image.readAsBytes();
  }

  Future<Uint8List?> pickFromGallery(BuildContext context) async {
    final permissions = _ref.read(devicePermissionsProvider);
    final outcome = await permissions.requestWithContext(context, DevicePermissionKind.storage);
    if (!outcome.granted) return null;
    final image = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null) return null;
    return image.readAsBytes();
  }

  Future<ProductImageUploadResult?> uploadForModel({
    required String productModelId,
    required Uint8List bytes,
    required String filename,
  }) async {
    return _ref.read(productImageRepositoryProvider).upload(
          productModelId: productModelId,
          filename: filename,
          bytes: bytes,
          mimeType: _mimeForFilename(filename),
        );
  }

  String? _mimeForFilename(String filename) {
    final lower = filename.toLowerCase();
    if (lower.endsWith('.png')) return 'image/png';
    if (lower.endsWith('.webp')) return 'image/webp';
    if (lower.endsWith('.gif')) return 'image/gif';
    return 'image/jpeg';
  }
}

final productImageActionsProvider = Provider<ProductImageActions>(
  (ref) => ProductImageActions(ref),
);

Future<void> showProductImageSheet(
  BuildContext context,
  WidgetRef ref, {
  required String productModelId,
  String? existingImageUrl,
  required Future<void> Function(String modelId, Map<String, dynamic> patch) onPatchModel,
}) async {
  final actions = ref.read(productImageActionsProvider);

  await showScrollableBottomSheet<void>(
    context: context,
    title: 'Product image',
    maxHeightFactor: 0.8,
    children: [
      if (existingImageUrl != null && existingImageUrl.isNotEmpty)
        Padding(
          padding: const EdgeInsets.all(16),
          child: ProductModelImage(imageUrl: existingImageUrl),
        ),
      ListTile(
        leading: const Icon(Icons.photo_camera_outlined),
        title: const Text('Capture photo'),
        onTap: () async {
          Navigator.pop(context);
          final bytes = await actions.captureFromCamera(context);
          if (bytes == null || !context.mounted) return;
          await _uploadAndPreview(context, ref, productModelId, bytes, 'capture.jpg');
        },
      ),
      if (existingImageUrl != null && existingImageUrl.isNotEmpty) ...[
        ListTile(
          leading: const Icon(Icons.fullscreen),
          title: const Text('Full screen preview'),
          onTap: () {
            Navigator.pop(context);
            Navigator.of(context).push<void>(
              MaterialPageRoute<void>(
                builder: (_) => ProductImageFullscreen(imageUrl: existingImageUrl),
              ),
            );
          },
        ),
        ListTile(
          leading: Icon(Icons.delete_outline, color: Theme.of(context).colorScheme.error),
          title: Text('Remove image', style: TextStyle(color: Theme.of(context).colorScheme.error)),
          onTap: () async {
            Navigator.pop(context);
            final messenger = ScaffoldMessenger.of(context);
            try {
              await onPatchModel(productModelId, {'product_image_url': null});
              if (!context.mounted) return;
              messenger.showSnackBar(const SnackBar(content: Text('Product image removed')));
            } catch (error) {
              messenger.showSnackBar(SnackBar(content: Text(error.toString())));
            }
          },
        ),
      ],
      ListTile(
        leading: const Icon(Icons.auto_awesome_outlined),
        title: const Text('Fetch image via AI'),
        onTap: () async {
          Navigator.pop(context);
          final messenger = ScaffoldMessenger.of(context);
          try {
            await ref.read(productImageRepositoryProvider).resolveViaAi(productModelId);
            if (!context.mounted) return;
            messenger.showSnackBar(const SnackBar(content: Text('AI image fetch requested')));
          } catch (error) {
            messenger.showSnackBar(SnackBar(content: Text(error.toString())));
          }
        },
      ),
      ListTile(
        leading: const Icon(Icons.photo_library_outlined),
        title: const Text('Choose from gallery'),
        onTap: () async {
          Navigator.pop(context);
          final bytes = await actions.pickFromGallery(context);
          if (bytes == null || !context.mounted) return;
          await _uploadAndPreview(context, ref, productModelId, bytes, 'gallery.jpg');
        },
      ),
    ],
  );
}

Future<void> _uploadAndPreview(
  BuildContext context,
  WidgetRef ref,
  String productModelId,
  Uint8List bytes,
  String filename,
) async {
  final messenger = ScaffoldMessenger.of(context);
  try {
    final result = await ref.read(productImageActionsProvider).uploadForModel(
          productModelId: productModelId,
          bytes: bytes,
          filename: filename,
        );
    if (!context.mounted || result == null) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Image uploaded'),
        content: ProductModelImage(imageUrl: result.productImageUrl),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Close')),
        ],
      ),
    );
  } catch (error) {
    messenger.showSnackBar(SnackBar(content: Text(error.toString())));
  }
}

class ProductImagePreview extends StatelessWidget {
  const ProductImagePreview({
    super.key,
    this.imageUrl,
    this.imageBytes,
    this.height = 180,
    this.fit = BoxFit.contain,
    this.onRetry,
    this.bordered = true,
    this.padding = const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
    this.onTap,
  }) : assert(imageUrl != null || imageBytes != null);

  final String? imageUrl;
  final Uint8List? imageBytes;
  final double height;
  final BoxFit fit;
  final VoidCallback? onRetry;
  final bool bordered;
  final EdgeInsets padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final frame = Container(
      height: height,
      width: double.infinity,
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLow,
        borderRadius: bordered ? BorderRadius.circular(12) : BorderRadius.zero,
        border: bordered ? Border.all(color: colorScheme.outlineVariant.withValues(alpha: 0.45)) : null,
      ),
      padding: padding,
      alignment: Alignment.center,
      child: imageBytes != null
          ? Image.memory(imageBytes!, fit: fit, alignment: Alignment.center)
          : Image.network(
              imageUrl!,
              fit: fit,
              alignment: Alignment.center,
              loadingBuilder: (context, child, progress) {
                if (progress == null) return child;
                return const Center(child: CircularProgressIndicator(strokeWidth: 2));
              },
              errorBuilder: (_, __, ___) => _errorPlaceholder(context),
            ),
    );

    if (onTap == null) return frame;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: bordered ? BorderRadius.circular(12) : BorderRadius.zero,
        child: frame,
      ),
    );
  }

  Widget _errorPlaceholder(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.image_not_supported_outlined, color: colorScheme.outline, size: 36),
        const SizedBox(height: 8),
        Text(
          'Image unavailable',
          style: Theme.of(context).textTheme.labelMedium?.copyWith(color: colorScheme.onSurfaceVariant),
        ),
        if (onRetry != null)
          TextButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    );
  }
}

/// Loads product images through the authenticated API proxy and shows them in a desktop-parity frame.
class ProductModelImage extends ConsumerStatefulWidget {
  const ProductModelImage({
    super.key,
    required this.imageUrl,
    this.height = 180,
    this.fit = BoxFit.contain,
    this.bordered = true,
    this.padding = const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
    this.allowFullscreen = false,
    this.modelName,
  });

  final String imageUrl;
  final double height;
  final BoxFit fit;
  final bool bordered;
  final EdgeInsets padding;
  final bool allowFullscreen;
  final String? modelName;

  @override
  ConsumerState<ProductModelImage> createState() => _ProductModelImageState();
}

class _ProductModelImageState extends ConsumerState<ProductModelImage> {
  Uint8List? _bytes;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ProductModelImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.imageUrl != widget.imageUrl) {
      _load();
    }
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _bytes = null;
    });
    final bytes = await ref.read(productImageRepositoryProvider).fetchImageBytes(widget.imageUrl);
    if (!mounted) return;
    setState(() {
      _bytes = bytes;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return SizedBox(
        height: widget.height,
        child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
      );
    }

    return ProductImagePreview(
      imageBytes: _bytes,
      height: widget.height,
      fit: widget.fit,
      bordered: widget.bordered,
      padding: widget.padding,
      onRetry: _load,
      onTap: widget.allowFullscreen && _bytes != null
          ? () {
              Navigator.of(context).push<void>(
                MaterialPageRoute<void>(
                  builder: (_) => ProductImageFullscreen(imageBytes: _bytes!),
                ),
              );
            }
          : null,
    );
  }
}

class ProductImageFullscreen extends ConsumerStatefulWidget {
  const ProductImageFullscreen({
    super.key,
    this.imageUrl,
    this.imageBytes,
  }) : assert(imageUrl != null || imageBytes != null);

  final String? imageUrl;
  final Uint8List? imageBytes;

  @override
  ConsumerState<ProductImageFullscreen> createState() => _ProductImageFullscreenState();
}

class _ProductImageFullscreenState extends ConsumerState<ProductImageFullscreen> {
  Uint8List? _bytes;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (widget.imageBytes != null) {
      setState(() {
        _bytes = widget.imageBytes;
        _loading = false;
      });
      return;
    }

    final bytes = await ref.read(productImageRepositoryProvider).fetchImageBytes(widget.imageUrl!);
    if (!mounted) return;
    setState(() {
      _bytes = bytes;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Colors.white))
          : _bytes == null
              ? const Center(child: Icon(Icons.image_not_supported_outlined, color: Colors.white54, size: 48))
              : InteractiveViewer(
                  minScale: 0.5,
                  maxScale: 4,
                  child: Center(
                    child: Image.memory(_bytes!, fit: BoxFit.contain),
                  ),
                ),
    );
  }
}
