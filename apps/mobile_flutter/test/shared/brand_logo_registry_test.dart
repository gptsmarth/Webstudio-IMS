import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/shared/catalogue/brand_logo_registry.dart';

void main() {
  test('resolves known brand logos as svg assets', () {
    expect(BrandLogoRegistry.svgForName('ASUS'), 'assets/brand-logos/asus.svg');
    expect(BrandLogoRegistry.svgForName('Dell'), 'assets/brand-logos/dell.svg');
    expect(BrandLogoRegistry.normalizeBrandKey('ASUS Laptops'), 'asus');
  });

  test('maps catalogue png filename to svg asset', () {
    final candidates = BrandLogoRegistry.assetCandidates(brandName: 'ASUS', logoFilename: 'asus.png');
    expect(candidates.first, 'assets/brand-logos/asus.svg');
    expect(candidates, contains('assets/brand-logos/default.svg'));
  });

  test('falls back to default when brand unknown', () {
    expect(BrandLogoRegistry.svgForName('Unknown Brand XYZ'), 'assets/brand-logos/default.svg');
  });
}
