import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../inventory/data/inventory_repository.dart';
import '../../inventory/domain/inventory_models.dart';

class ReportFilterReference {
  const ReportFilterReference({
    required this.brands,
    required this.locations,
    required this.productModels,
  });

  final List<Brand> brands;
  final List<Location> locations;
  final List<ProductModel> productModels;
}

final reportFilterReferenceProvider = FutureProvider.autoDispose<ReportFilterReference>((ref) async {
  final repo = ref.watch(inventoryRepositoryProvider);
  try {
    final results = await Future.wait([
      repo.listBrands(),
      repo.listLocations(),
      repo.listProductModels(),
    ]);
    return ReportFilterReference(
      brands: results[0] as List<Brand>,
      locations: results[1] as List<Location>,
      productModels: results[2] as List<ProductModel>,
    );
  } catch (_) {
    return const ReportFilterReference(brands: [], locations: [], productModels: []);
  }
});
