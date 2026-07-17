/// Brand logo asset paths — mirrors desktop `BrandLogoRegistry` / `AssetManifest`.
///
/// Note: bundled `*.png` files in this repo are SVG content (desktop convention).
/// Mobile always loads `.svg` via [flutter_svg] for correct rendering on Android/iOS.
abstract final class BrandLogoRegistry {
  static const _base = 'assets/brand-logos';

  static const Set<String> _knownKeys = {
    'asus',
    'acer',
    'hp',
    'dell',
    'lenovo',
    'msi',
    'apple',
    'sandisk',
    'logitech',
    'tp-link',
    'canon',
    'epson',
    'brother',
  };

  static String normalizeBrandKey(String brandName) {
    final trimmed = brandName.trim().toLowerCase();
    if (_knownKeys.contains(trimmed)) return trimmed;

    final firstToken = trimmed.split(RegExp(r'[\s\-_/]+')).firstWhere((part) => part.isNotEmpty, orElse: () => trimmed);
    if (_knownKeys.contains(firstToken)) return firstToken;

    for (final key in _knownKeys) {
      if (trimmed.contains(key)) return key;
    }
    return firstToken;
  }

  static String svgForName(String brandName) {
    final key = normalizeBrandKey(brandName);
    if (_knownKeys.contains(key)) return '$_base/$key.svg';
    return '$_base/default.svg';
  }

  static String assetForFilename(String? logoFilename) {
    if (logoFilename == null || logoFilename.trim().isEmpty) {
      return '$_base/default.svg';
    }
    final file = logoFilename.trim().split('/').last;
    if (file.startsWith('assets/')) return file;
    // Catalogue may store `.png` names that are SVG bytes — prefer `.svg` sibling.
    if (file.toLowerCase().endsWith('.png')) {
      final stem = file.substring(0, file.length - 4);
      if (_knownKeys.contains(stem.toLowerCase())) {
        return '$_base/$stem.svg';
      }
    }
    return '$_base/$file';
  }

  static List<String> assetCandidates({required String brandName, String? logoFilename}) {
    final seen = <String>{};
    final candidates = <String>[];

    void add(String path) {
      final normalized = path.toLowerCase().endsWith('.png')
          ? path.replaceAll(RegExp(r'\.png$', caseSensitive: false), '.svg')
          : path;
      if (seen.add(normalized)) candidates.add(normalized);
    }

    if (logoFilename != null && logoFilename.trim().isNotEmpty) {
      add(assetForFilename(logoFilename));
    }

    add(svgForName(brandName));
    add('$_base/default.svg');
    return candidates;
  }

  static bool isSvgAsset(String path) => path.toLowerCase().endsWith('.svg');

  /// True when logo_filename points at a server-managed, user-uploaded logo
  /// (`/assets/brand-logos/brand-{id}.{ext}`) rather than a bundled asset.
  /// Uploaded logos are fetched through the authenticated image proxy.
  static bool isUploadedLogo(String? logoFilename) {
    final trimmed = logoFilename?.trim();
    return trimmed != null && trimmed.startsWith('/assets/brand-logos/brand-');
  }
}
