import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../ai/data/ai_enrichment_repository.dart';
import '../../../media/data/product_image_repository.dart';
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
  late final TextEditingController _display;
  late final TextEditingController _colorOptions;
  late final TextEditingController _imageUrl;
  late final TextEditingController _sellingPrice;
  late final TextEditingController _livePrice;
  late final TextEditingController _purchasePrice;
  late final TextEditingController _notes;
  late int? _brandId;
  String _storageUnit = 'GB';
  String _storageType = 'SSD';
  bool _loadingAi = false;
  bool _fetchingImage = false;
  bool _saving = false;
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
    _display = TextEditingController(text: m?.display ?? '');
    _colorOptions = TextEditingController(text: m?.colorOptions ?? '');
    _imageUrl = TextEditingController(text: m?.productImageUrl ?? '');
    _sellingPrice = TextEditingController(text: m?.sellingPrice?.toString() ?? '');
    _livePrice = TextEditingController(text: m?.livePrice?.toString() ?? '');
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
    _display.dispose();
    _colorOptions.dispose();
    _imageUrl.dispose();
    _sellingPrice.dispose();
    _livePrice.dispose();
    _purchasePrice.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _fetchSpecs() async {
    if (_brandId == null || _modelNumber.text.trim().isEmpty) return;
    setState(() {
      _loadingAi = true;
      _error = null;
    });
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
        _display.text = result['display']?.toString() ?? _display.text;
        _colorOptions.text = result['color_options']?.toString() ?? _colorOptions.text;
        final image = result['product_image_url']?.toString();
        if (image != null && image.isNotEmpty) {
          _imageUrl.text = image;
        }
        _notes.text = result['notes']?.toString() ?? _notes.text;
        _loadingAi = false;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _loadingAi = false;
          _error = error.toString();
        });
      }
    }
  }

  Future<void> _fetchImageInBackground() async {
    final existing = widget.existing;
    if (existing == null) return;
    if (_fetchingImage) return;
    setState(() => _fetchingImage = true);
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      const SnackBar(content: Text('Fetching product image in the background…')),
    );
    try {
      // Kick off non-blocking discovery; poll briefly for a result without freezing UI.
      final repo = ref.read(productImageRepositoryProvider);
      await repo.resolveViaAi(existing.id, wait: false);
      final url = await repo.resolveAndWaitForImage(
        existing.id,
        timeout: const Duration(seconds: 30),
        pollInterval: const Duration(seconds: 2),
      );
      if (!mounted) return;
      if (url != null && url.isNotEmpty) {
        setState(() => _imageUrl.text = url);
        await ref.read(widget.workspaceProvider.notifier).updateProductModel(
          existing.id,
          {'product_image_url': url},
        );
        if (!mounted) return;
        messenger.showSnackBar(const SnackBar(content: Text('Product image updated')));
      } else {
        messenger.showSnackBar(
          const SnackBar(content: Text('No suitable product image was found')),
        );
      }
    } catch (error) {
      if (mounted) {
        messenger.showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => _fetchingImage = false);
    }
  }

  Map<String, dynamic> _payload() => {
        'brand_id': _brandId,
        'model_number': _modelNumber.text.trim(),
        'model_name': _modelName.text.trim(),
        'cpu': _cpu.text.trim().isEmpty ? '—' : _cpu.text.trim(),
        if (_gpu.text.trim().isNotEmpty) 'gpu': _gpu.text.trim(),
        'ram_gb': int.tryParse(_ram.text.trim()) ?? 8,
        'storage_value': _storage.text.trim().isEmpty ? '1' : _storage.text.trim(),
        'storage_unit': _storageUnit,
        'storage_type': _storageType,
        if (_display.text.trim().isNotEmpty) 'display': _display.text.trim(),
        if (_colorOptions.text.trim().isNotEmpty) 'color_options': _colorOptions.text.trim(),
        if (_imageUrl.text.trim().isNotEmpty) 'product_image_url': _imageUrl.text.trim(),
        if (_imageUrl.text.trim().isEmpty && widget.existing != null) 'product_image_url': null,
        if (_sellingPrice.text.trim().isNotEmpty)
          'selling_price': double.tryParse(_sellingPrice.text.trim()),
        if (_purchasePrice.text.trim().isNotEmpty)
          'purchase_price': double.tryParse(_purchasePrice.text.trim()),
        if (_notes.text.trim().isNotEmpty) 'notes': _notes.text.trim(),
      };

  InputDecoration _field(String label) => InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      );

  Widget _gap() => const SizedBox(height: AppSpacing.md);

  @override
  Widget build(BuildContext context) {
    final isEdit = widget.existing != null;
    final ctrl = ref.read(widget.workspaceProvider.notifier);
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.92,
      minChildSize: 0.55,
      maxChildSize: 0.96,
      builder: (context, scrollController) => ListView(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.lg, AppSpacing.xl, AppSpacing.xxl),
        children: [
          Text(
            isEdit ? 'Edit product model' : 'Create product model',
            style: theme.textTheme.titleLarge,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Same fields as desktop — update specs, prices, and image.',
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          if (_error != null) ...[
            _gap(),
            Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
          ],
          _gap(),
          DropdownButtonFormField<int>(
            value: _brandId,
            decoration: _field('Brand'),
            items: widget.brands
                .map((b) => DropdownMenuItem(value: b.id, child: Text(b.name)))
                .toList(),
            onChanged: (v) => setState(() => _brandId = v),
          ),
          _gap(),
          TextField(controller: _modelNumber, decoration: _field('Model number')),
          _gap(),
          TextField(controller: _modelName, decoration: _field('Model name')),
          _gap(),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              OutlinedButton.icon(
                onPressed: _loadingAi ? null : _fetchSpecs,
                icon: _loadingAi
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.auto_awesome_outlined, size: 18),
                label: const Text('Fetch specs'),
              ),
              if (isEdit)
                OutlinedButton.icon(
                  onPressed: _fetchingImage ? null : _fetchImageInBackground,
                  icon: _fetchingImage
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.image_search_outlined, size: 18),
                  label: const Text('Fetch image'),
                ),
              if (isEdit)
                OutlinedButton.icon(
                  onPressed: () => showProductImageSheet(
                    context,
                    ref,
                    productModelId: widget.existing!.id,
                    existingImageUrl: _imageUrl.text.trim().isEmpty ? null : _imageUrl.text.trim(),
                    onPatchModel: (modelId, patch) async {
                      await ctrl.updateProductModel(modelId, patch);
                      final url = patch['product_image_url'] as String?;
                      if (mounted) {
                        setState(() => _imageUrl.text = url ?? '');
                      }
                    },
                  ),
                  icon: const Icon(Icons.photo_camera_outlined, size: 18),
                  label: const Text('Photo / gallery'),
                ),
            ],
          ),
          _gap(),
          TextField(controller: _cpu, decoration: _field('Processor (CPU)')),
          _gap(),
          TextField(controller: _gpu, decoration: _field('Graphics (GPU)')),
          _gap(),
          TextField(
            controller: _ram,
            decoration: _field('RAM (GB)'),
            keyboardType: TextInputType.number,
          ),
          _gap(),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: TextField(
                  controller: _storage,
                  decoration: _field('Storage size'),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _storageUnit,
                  decoration: _field('Unit'),
                  items: const [
                    DropdownMenuItem(value: 'GB', child: Text('GB')),
                    DropdownMenuItem(value: 'TB', child: Text('TB')),
                  ],
                  onChanged: (v) => setState(() => _storageUnit = v ?? 'GB'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _storageType == 'NVMe' || _storageType == 'eMMC' ? 'SSD' : _storageType,
                  decoration: _field('Type'),
                  items: const [
                    DropdownMenuItem(value: 'SSD', child: Text('SSD')),
                    DropdownMenuItem(value: 'HDD', child: Text('HDD')),
                  ],
                  onChanged: (v) => setState(() => _storageType = v ?? 'SSD'),
                ),
              ),
            ],
          ),
          _gap(),
          TextField(controller: _display, decoration: _field('Display')),
          _gap(),
          TextField(controller: _colorOptions, decoration: _field('Color options')),
          _gap(),
          TextField(controller: _imageUrl, decoration: _field('Image URL')),
          if (_imageUrl.text.trim().isNotEmpty) ...[
            const SizedBox(height: AppSpacing.sm),
            ProductModelImage(imageUrl: _imageUrl.text.trim(), height: 140),
          ],
          _gap(),
          TextField(
            controller: _purchasePrice,
            decoration: _field('Purchase / cost price (INR)'),
            keyboardType: TextInputType.number,
          ),
          _gap(),
          TextField(
            controller: _sellingPrice,
            decoration: _field('Selling price (INR)'),
            keyboardType: TextInputType.number,
          ),
          if (isEdit && widget.existing!.isAsusLaptop) ...[
            _gap(),
            TextField(
              controller: _livePrice,
              decoration: _field('ASUS price (manual)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              widget.existing!.livePriceStatus == 'manual'
                  ? 'Manually entered — the next successful automatic refresh overwrites it.'
                  : 'For when the automatic ASUS search comes back NA or wrong.',
              style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
          _gap(),
          TextField(
            controller: _notes,
            decoration: _field('Notes'),
            maxLines: 3,
          ),
          const SizedBox(height: AppSpacing.xl),
          FilledButton(
            onPressed: _saving
                ? null
                : () async {
                    if (_brandId == null ||
                        _modelNumber.text.trim().isEmpty ||
                        _modelName.text.trim().isEmpty) {
                      setState(() => _error = 'Brand, model number, and model name are required.');
                      return;
                    }
                    setState(() {
                      _saving = true;
                      _error = null;
                    });
                    try {
                      if (isEdit) {
                        await ctrl.updateProductModel(widget.existing!.id, _payload());
                        if (widget.existing!.isAsusLaptop) {
                          final parsedLive = _livePrice.text.trim().isEmpty
                              ? null
                              : double.tryParse(_livePrice.text.trim());
                          if (parsedLive != widget.existing!.livePrice) {
                            await ctrl.updateLivePrice(widget.existing!.id, parsedLive);
                          }
                        }
                      } else {
                        await ctrl.createProductModel(_payload());
                      }
                      if (context.mounted) Navigator.pop(context);
                    } catch (error) {
                      if (mounted) {
                        setState(() {
                          _saving = false;
                          _error = error.toString();
                        });
                      }
                    }
                  },
            child: _saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(isEdit ? 'Save changes' : 'Create model'),
          ),
        ],
      ),
    );
  }
}
