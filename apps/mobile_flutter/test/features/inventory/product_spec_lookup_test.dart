import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/features/inventory/domain/inventory_models.dart';
import 'package:webstudio_ims/features/inventory/domain/product_spec_lookup.dart';

void main() {
  test('findModelByNumber matches within brand only', () {
    const models = [
      ProductModel(
        id: '1',
        brandId: 1,
        modelNumber: 'X515EA',
        modelName: 'Vivobook',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
      ProductModel(
        id: '2',
        brandId: 2,
        modelNumber: 'X515EA',
        modelName: 'IdeaPad',
        cpu: 'i5',
        ramGb: 16,
        storageValue: '512',
        storageUnit: 'GB',
        storageType: 'SSD',
        status: 'active',
      ),
    ];

    expect(findModelByNumber(models, 'x515ea', brandId: 1)?.id, '1');
    expect(findModelByNumber(models, 'x515ea', brandId: 2)?.id, '2');
    expect(findModelByNumber(models, 'missing', brandId: 1), isNull);
  });

  test('defaultUnitColorFromOptions respects 64-char API limit', () {
    expect(defaultUnitColorFromOptions(null), 'Not specified');
    expect(defaultUnitColorFromOptions('Black, Silver'), 'Black');
    expect(defaultUnitColorFromOptions('Quiet Blue / Silver'), 'Quiet Blue');
    final long = 'A' * 80;
    expect(defaultUnitColorFromOptions(long).length, kInventoryColorMaxLength);
  });
}
