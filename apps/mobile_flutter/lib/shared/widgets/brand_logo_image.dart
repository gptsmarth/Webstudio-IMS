import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../features/media/data/product_image_repository.dart';
import '../catalogue/brand_logo_registry.dart';

class BrandLogoImage extends ConsumerStatefulWidget {
  const BrandLogoImage({
    super.key,
    required this.brandName,
    this.logoFilename,
    this.height = 56,
    this.maxWidth = 120,
  });

  final String brandName;
  final String? logoFilename;
  final double height;
  final double maxWidth;

  @override
  ConsumerState<BrandLogoImage> createState() => _BrandLogoImageState();
}

class _BrandLogoImageState extends ConsumerState<BrandLogoImage> {
  late List<String> _candidates = _buildCandidates();
  int _candidateIndex = 0;
  Uint8List? _uploadedBytes;
  bool _uploadedFailed = false;

  List<String> _buildCandidates() {
    return BrandLogoRegistry.assetCandidates(
      brandName: widget.brandName,
      logoFilename: widget.logoFilename,
    );
  }

  @override
  void initState() {
    super.initState();
    _maybeLoadUploaded();
  }

  bool get _isUploaded => BrandLogoRegistry.isUploadedLogo(widget.logoFilename);

  Future<void> _maybeLoadUploaded() async {
    if (!_isUploaded || widget.logoFilename == null) return;
    final bytes =
        await ref.read(productImageRepositoryProvider).fetchImageBytes(widget.logoFilename!);
    if (!mounted) return;
    setState(() {
      _uploadedBytes = bytes;
      _uploadedFailed = bytes == null;
    });
  }

  @override
  void didUpdateWidget(covariant BrandLogoImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.brandName != widget.brandName || oldWidget.logoFilename != widget.logoFilename) {
      setState(() {
        _candidates = _buildCandidates();
        _candidateIndex = 0;
        _uploadedBytes = null;
        _uploadedFailed = false;
      });
      _maybeLoadUploaded();
    }
  }

  void _tryNextCandidate() {
    if (_candidateIndex >= _candidates.length - 1) return;
    setState(() => _candidateIndex++);
  }

  @override
  Widget build(BuildContext context) {
    // Server-uploaded logo: render bytes fetched via the authenticated proxy.
    // Fall through to bundled candidates while loading or if the fetch failed.
    if (_isUploaded && !_uploadedFailed) {
      if (_uploadedBytes != null) {
        return Image.memory(
          _uploadedBytes!,
          height: widget.height,
          width: widget.maxWidth,
          fit: BoxFit.contain,
          gaplessPlayback: true,
          errorBuilder: (_, __, ___) => _PlaceholderIcon(size: widget.height),
        );
      }
      return SizedBox(
        height: widget.height,
        width: widget.maxWidth,
        child: Center(child: _PlaceholderIcon(size: widget.height)),
      );
    }

    final path = _candidates[_candidateIndex];
    if (BrandLogoRegistry.isSvgAsset(path)) {
      return SizedBox(
        height: widget.height,
        width: widget.maxWidth,
        child: SvgPicture.asset(
          path,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) _tryNextCandidate();
            });
            return _PlaceholderIcon(size: widget.height);
          },
        ),
      );
    }

    return Image.asset(
      path,
      height: widget.height,
      width: widget.maxWidth,
      fit: BoxFit.contain,
      gaplessPlayback: true,
      errorBuilder: (_, __, ___) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _tryNextCandidate();
        });
        return _PlaceholderIcon(size: widget.height);
      },
    );
  }
}

class _PlaceholderIcon extends StatelessWidget {
  const _PlaceholderIcon({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Icon(
      Icons.storefront_outlined,
      size: size * 0.65,
      color: Theme.of(context).colorScheme.outline,
    );
  }
}
