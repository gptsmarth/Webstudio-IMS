import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../catalogue/brand_logo_registry.dart';

class BrandLogoImage extends StatefulWidget {
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
  State<BrandLogoImage> createState() => _BrandLogoImageState();
}

class _BrandLogoImageState extends State<BrandLogoImage> {
  late final List<String> _candidates = BrandLogoRegistry.assetCandidates(
    brandName: widget.brandName,
    logoFilename: widget.logoFilename,
  );
  int _candidateIndex = 0;

  @override
  void didUpdateWidget(covariant BrandLogoImage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.brandName != widget.brandName || oldWidget.logoFilename != widget.logoFilename) {
      setState(() => _candidateIndex = 0);
    }
  }

  void _tryNextCandidate() {
    if (_candidateIndex >= _candidates.length - 1) return;
    setState(() => _candidateIndex++);
  }

  @override
  Widget build(BuildContext context) {
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
