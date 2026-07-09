import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../ai/data/ai_enrichment_repository.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../domain/inventory_models.dart';
import '../inventory_controller.dart';

Future<void> showProductModelFormSheet(
  BuildContext context,
  WidgetRef ref, {
  required InventoryWorkspaceProvider workspaceProvider,
  ProductModel? existing,
  int? defaultBrandId,
}) async {
  final brands = ref.read(workspaceProvider).brands;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _ProductModelFormSheet(
      existing: existing,
      brands: brands,
      defaultBrandId: defaultBrandId,
      workspaceProvider: workspaceProvider,
    ),
  );
}

class _ProductModelFormSheet extends ConsumerStatefulWidget {
  const _ProductModelFormSheet({
    this.existing,
    required this.brands,
    this.defaultBrandId,
    required this.workspaceProvider,
  });

  final ProductModel? existing;
  final List<Brand> brands;
  final int? defaultBrandId;
  final InventoryWorkspaceProvider workspaceProvider;

  @override
  ConsumerState<_ProductModelFormSheet> createState() => _ProductModelFormSheetState();
}

class _ProductModelFormSheetState extends ConsumerState<_ProductModelFormSheet> {
  late final TextEditingController _modelNumber;
  late final TextEditingController _modelName;
  late final TextEditingController _cpu;
  late final TextEditingController _gpu;
  late final TextEditingController _ram;
  late final TextEditingController _storage;
  late final TextEditingController _sellingPrice;
  late final TextEditingController _purchasePrice;
  late final TextEditingController _notes;
  late int? _brandId;
  String _storageUnit = 'GB';
  String _storageType = 'SSD';
  bool _loadingAi = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final m = widget.existing;
    _modelNumber = TextEditingController(text: m?.modelNumber ?? '');
    _modelName = TextEditingController(text: m?.modelName ?? '');
    _cpu = TextEditingController(text: m?.cpu ?? '');
    _gpu = TextEditingController(text: m?.gpu ?? '');
    _ram = TextEditingController(text: m?.ramGb.toString() ?? '');
    _storage = TextEditingController(text: m?.storageValue ?? '512');
    _sellingPrice = TextEditingController(text: m?.sellingPrice?.toString() ?? '');
    _purchasePrice = TextEditingController(text: m?.purchasePrice?.toString() ?? '');
    _notes = TextEditingController(text: m?.notes ?? '');
    _brandId = m?.brandId ?? widget.defaultBrandId ?? (widget.brands.isNotEmpty ? widget.brands.first.id : null);
    if (m != null) {
      _storageUnit = m.storageUnit;
      _storageType = m.storageType;
    }
  }

  @override
  void dispose() {
    _modelNumber.dispose();
    _modelName.dispose();
    _cpu.dispose();
    _gpu.dispose();
    _ram.dispose();
    _storage.dispose();
    _sellingPrice.dispose();
    _purchasePrice.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _fetchSpecs() async {
    if (_brandId == null || _modelNumber.text.trim().isEmpty) return;
    setState(() => _loadingAi = true);
    try {
      final brand = widget.brands.firstWhere((b) => b.id == _brandId);
      final result = await ref.read(aiEnrichmentRepositoryProvider).lookupSpecs(
            brandName: brand.name,
            modelNumber: _modelNumber.text.trim(),
            modelName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
            forceRefresh: true,
          );
      if (!mounted) return;
      setState(() {
        _modelName.text = result['model_name']?.toString() ?? _modelName.text;
        _cpu.text = result['cpu']?.toString() ?? _cpu.text;
        _gpu.text = result['gpu']?.toString() ?? _gpu.text;
        _ram.text = result['ram_gb']?.toString() ?? _ram.text;
        _storage.text = result['storage_value']?.toString() ?? _storage.text;
        _storageUnit = result['storage_unit']?.toString() ?? _storageUnit;
        _storageType = result['storage_type']?.toString() ?? _storageType;
        _notes.text = result['notes']?.toString() ?? _notes.text;
        _loadingAi = false;
      });
    } catch (error) {
      if (mounted) setState(() { _loadingAi = false; _error = error.toString(); });
    }
  }

  Map<String, dynamic> _payload() => {
        'brand_id': _brandId,
        'model_number': _modelNumber.text.trim(),
        'model_name': _modelName.text.trim(),
        'cpu': _cpu.text.trim(),
        if (_gpu.text.trim().isNotEmpty) 'gpu': _gpu.text.trim(),
        'ram_gb': int.tryParse(_ram.text.trim()) ?? 8,
        'storage_value': _storage.text.trim(),
        'storage_unit': _storageUnit,
        'storage_type': _storageType,
        if (_sellingPrice.text.trim().isNotEmpty) 'selling_price': double.tryParse(_sellingPrice.text.trim()),
        if (_purchasePrice.text.trim().isNotEmpty) 'purchase_price': double.tryParse(_purchasePrice.text.trim()),
        if (_notes.text.trim().isNotEmpty) 'notes': _notes.text.trim(),
      };

  @override
  Widget build(BuildContext context) {
    final isEdit = widget.existing != null;
    final ctrl = ref.read(widget.workspaceProvider.notifier);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) => ListView(
        controller: scrollController,
        padding: const EdgeInsets.all(AppSpacing.xl),
        children: [
          Text(isEdit ? 'Edit product model' : 'Create product model', style: Theme.of(context).textTheme.titleLarge),
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          DropdownButtonFormField<int>(
            value: _brandId,
            decoration: const InputDecoration(labelText: 'Brand'),
            items: widget.brands.map((b) => DropdownMenuItem(value: b.id, child: Text(b.name))).toList(),
            onChanged: (v) => setState(() => _brandId = v),
          ),
          TextField(controller: _modelNumber, decoration: const InputDecoration(labelText: 'Model number')),
          TextField(controller: _modelName, decoration: const InputDecoration(labelText: 'Model name')),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _loadingAi ? null : _fetchSpecs,
                  icon: _loadingAi
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_outlined, size: 18),
                  label: const Text('AI specs'),
                ),
              ),
              if (isEdit)
                IconButton(
                  icon: const Icon(Icons.photo_camera_outlined),
                  onPressed: () => showProductImageSheet(
                    context,
                    ref,
                    productModelId: widget.existing!.id,
                    existingImageUrl: widget.existing!.productImageUrl,
                    onPatchModel: ctrl.updateProductModel,
                  ),
                ),
            ],
          ),
          TextField(controller: _cpu, decoration: const InputDecoration(labelText: 'CPU')),
          TextField(controller: _gpu, decoration: const InputDecoration(labelText: 'GPU')),
          TextField(controller: _ram, decoration: const InputDecoration(labelText: 'RAM (GB)'), keyboardType: TextInputType.number),
          TextField(controller: _storage, decoration: const InputDecoration(labelText: 'Storage')),
          TextField(controller: _sellingPrice, decoration: const InputDecoration(labelText: 'Selling price'), keyboardType: TextInputType.number),
          TextField(controller: _purchasePrice, decoration: const InputDecoration(labelText: 'Cost price'), keyboardType: TextInputType.number),
          TextField(controller: _notes, decoration: const InputDecoration(labelText: 'Notes'), maxLines: 3),
          const SizedBox(height: AppSpacing.lg),
          FilledButton(
            onPressed: () async {
              if (isEdit) {
                await ctrl.updateProductModel(widget.existing!.id, _payload());
              } else {
                await ctrl.createProductModel(_payload());
              }
              if (context.mounted) Navigator.pop(context);
            },
            child: Text(isEdit ? 'Save changes' : 'Create model'),
          ),
        ],
      ),
    );
  }
}
