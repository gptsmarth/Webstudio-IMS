import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_exception.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../ai/data/ai_enrichment_repository.dart';
import '../../../inventory/data/inventory_repository.dart';
import '../../../inventory/domain/accessory_spec_lookup.dart';
import '../../../inventory/domain/inventory_models.dart';
import '../../../inventory/domain/product_category.dart';
import '../../../inventory/domain/product_spec_lookup.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../data/purchase_repository.dart';
import '../../domain/purchase_models.dart';

/// Remove a single leading brand token from a raw Tally stock item name so the
/// brand (e.g. "ASUS") is not carried into the seeded model number/name or the
/// internet spec lookup. Mirrors the backend deterministic normalizer: the
/// prefix is stripped only at a real word boundary (space or hyphen).
String stripBrandPrefixForSeed(String value, String? brandName) {
  final out = value.trim().replaceAll(RegExp(r'\s+'), ' ');
  final brand = (brandName ?? '').trim().replaceAll(RegExp(r'\s+'), ' ');
  if (out.isEmpty || brand.isEmpty) return out;
  final upperOut = out.toUpperCase();
  final upperBrand = brand.toUpperCase();
  if (upperOut == upperBrand) return out; // whole value is the brand — keep it
  for (final sep in const [' ', '-']) {
    if (upperOut.startsWith('$upperBrand$sep')) {
      return out.substring(brand.length).replaceAll(RegExp(r'^[\s-]+'), '').trim();
    }
  }
  return out;
}

/// Opens the Purchase Import flow for a single model group.
/// Reuses the shared `/purchase/import` backend contract (existing-append and
/// new-model creation both happen server-side in one transaction).
Future<void> showPurchaseImportSheet(
  BuildContext context,
  WidgetRef ref, {
  required PurchaseVoucherDetail voucher,
  required PurchaseModelGroup group,
  required VoidCallback onImported,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: _PurchaseImportSheet(voucher: voucher, group: group, onImported: onImported),
    ),
  );
}

class _PurchaseImportSheet extends ConsumerStatefulWidget {
  const _PurchaseImportSheet({
    required this.voucher,
    required this.group,
    required this.onImported,
  });

  final PurchaseVoucherDetail voucher;
  final PurchaseModelGroup group;
  final VoidCallback onImported;

  @override
  ConsumerState<_PurchaseImportSheet> createState() => _PurchaseImportSheetState();
}

class _PurchaseImportSheetState extends ConsumerState<_PurchaseImportSheet> {
  List<Brand> _brands = const [];
  List<Location> _locations = const [];
  List<ProductModel> _brandModels = const [];

  bool _loading = true;
  int _brandId = 0;
  String _itemType = ''; // 'laptop' | 'accessory'
  MatchModelResponse? _match;
  MatchAccessoryResponse? _accMatch;
  bool _matching = false;
  String? _mode; // 'existing' | 'new'
  String? _selectedModelId;

  final List<TextEditingController> _serials = [];
  int _locationId = 0;
  final _purchasePrice = TextEditingController();
  String _status = 'available';

  // New-model spec fields.
  final _modelNumber = TextEditingController();
  final _modelName = TextEditingController();
  final _partNumber = TextEditingController();
  AccessoryKind? _accessoryKind;
  final _cpu = TextEditingController();
  final _gpu = TextEditingController();
  final _ramGb = TextEditingController(text: '16');
  final _storageValue = TextEditingController(text: '512');
  final _display = TextEditingController();
  final _colorOptions = TextEditingController();
  final _specNotes = TextEditingController();
  String _storageUnit = 'GB';
  String _storageType = 'SSD';
  String? _productImageUrl;
  bool _fetching = false;
  String? _specMessage;

  bool _submitting = false;
  String? _error;

  late final Set<String> _knownDuplicates = {
    for (final cell in widget.group.serials)
      if (cell.isDuplicate) cell.serialNumber.trim().toUpperCase(),
  };

  @override
  void initState() {
    super.initState();
    for (final cell in widget.group.serials) {
      _serials.add(TextEditingController(text: cell.serialNumber));
    }
    if (_serials.isEmpty) _serials.add(TextEditingController());
    _purchasePrice.text = _defaultUnitPrice();
    _loadReferenceData();
  }

  @override
  void dispose() {
    for (final controller in _serials) {
      controller.dispose();
    }
    _purchasePrice.dispose();
    _modelNumber.dispose();
    _modelName.dispose();
    _partNumber.dispose();
    _cpu.dispose();
    _gpu.dispose();
    _ramGb.dispose();
    _storageValue.dispose();
    _display.dispose();
    _colorOptions.dispose();
    _specNotes.dispose();
    super.dispose();
  }

  /// Per-unit purchase price from Tally = line total ÷ quantity. Always editable.
  String _defaultUnitPrice() {
    final total = widget.group.lineTotal;
    final qty = widget.group.quantity > 0 ? widget.group.quantity : _serials.length;
    if (total == null || total <= 0 || qty <= 0) return '';
    final unit = total / qty;
    if (!unit.isFinite || unit <= 0) return '';
    var text = unit.toStringAsFixed(2);
    if (text.endsWith('.00')) {
      text = text.substring(0, text.length - 3);
    } else if (text.endsWith('0')) {
      text = text.substring(0, text.length - 1);
    }
    return text;
  }

  Future<void> _loadReferenceData() async {
    try {
      final repo = ref.read(inventoryRepositoryProvider);
      final results = await Future.wait([repo.listBrands(), repo.listLocations()]);
      if (!mounted) return;
      setState(() {
        _brands = (results[0] as List<Brand>).where((b) => b.isActive).toList();
        _locations = results[1] as List<Location>;
        _locationId = _locations.isNotEmpty ? _locations.first.id : 0;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = formatApiError(error);
      });
    }
  }

  Future<void> _onBrandChanged(int brandId) async {
    setState(() {
      _brandId = brandId;
      _itemType = '';
      _match = null;
      _accMatch = null;
      _mode = null;
      _selectedModelId = null;
      _brandModels = const [];
      _error = null;
    });
    if (brandId <= 0) return;
    try {
      final allModels = await ref.read(inventoryRepositoryProvider).listProductModels();
      if (!mounted) return;
      setState(() {
        _brandModels = allModels.where((m) => m.brandId == brandId).toList();
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = formatApiError(error));
    }
  }

  String? get _brandName => _brands.where((b) => b.id == _brandId).map((b) => b.name).firstOrNull;

  Future<void> _chooseItemType(String next) async {
    setState(() {
      _itemType = next;
      _match = null;
      _accMatch = null;
      _mode = null;
      _selectedModelId = null;
      _error = null;
    });
    if (_brandId <= 0) return;
    setState(() => _matching = true);
    try {
      final repo = ref.read(purchaseRepositoryProvider);
      if (next == 'laptop') {
        final match =
            await repo.matchModel(brandId: _brandId, modelNumber: widget.group.stockItemName);
        if (!mounted) return;
        setState(() {
          _match = match;
          _matching = false;
          if (match.autoSelectedModelId != null) {
            _mode = 'existing';
            _selectedModelId = match.autoSelectedModelId;
          }
        });
      } else {
        final match =
            await repo.matchAccessory(brandId: _brandId, query: widget.group.stockItemName);
        if (!mounted) return;
        setState(() {
          _accMatch = match;
          _matching = false;
          if (match.autoSelectedModelId != null) {
            _mode = 'existing';
            _selectedModelId = match.autoSelectedModelId;
          }
        });
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _matching = false;
        _error = formatApiError(error);
      });
    }
  }

  Future<void> _runAutoFetch() async {
    final brand = _brands.where((b) => b.id == _brandId).map((b) => b.name).firstOrNull;
    final modelNumber = _modelNumber.text.trim();
    if (brand == null || modelNumber.isEmpty) return;
    setState(() {
      _fetching = true;
      _specMessage = null;
    });
    try {
      final raw = await ref.read(aiEnrichmentRepositoryProvider).lookupSpecs(
            brandName: brand,
            modelNumber: modelNumber,
            modelName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
            forceRefresh: true,
          );
      final spec = FetchedProductSpec.fromApi(raw);
      if (!mounted) return;
      setState(() {
        _fetching = false;
        if (spec.cpu.trim().isEmpty) {
          _specMessage = 'Auto-fetch found no match — enter details manually.';
          return;
        }
        if (spec.modelName.isNotEmpty) _modelName.text = spec.modelName;
        _cpu.text = spec.cpu;
        _gpu.text = spec.gpu ?? '';
        _ramGb.text = '${spec.ramGb}';
        _storageValue.text = spec.storageValue;
        _storageUnit = spec.storageUnit == 'TB' ? 'TB' : 'GB';
        _storageType = spec.storageType == 'HDD' ? 'HDD' : 'SSD';
        _display.text = spec.display ?? '';
        _colorOptions.text = spec.colorOptions ?? '';
        _specNotes.text = spec.notes ?? '';
        _productImageUrl = spec.productImageUrl;
        _specMessage = 'Configuration fetched — review and adjust if needed.';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _fetching = false;
        _specMessage = 'Auto-fetch failed — enter details manually.';
      });
    }
  }

  Future<void> _runAccessoryAutoFetch() async {
    final brand = _brands.where((b) => b.id == _brandId).map((b) => b.name).firstOrNull;
    final identifier = _partNumber.text.trim().isNotEmpty
        ? _partNumber.text.trim()
        : _modelNumber.text.trim();
    if (brand == null || identifier.isEmpty) return;
    setState(() {
      _fetching = true;
      _specMessage = null;
    });
    try {
      final raw = await ref.read(aiEnrichmentRepositoryProvider).lookupAccessorySpec(
            identifier: identifier,
            identifierType: _partNumber.text.trim().isNotEmpty
                ? AccessoryIdentifierType.partNumber
                : AccessoryIdentifierType.modelNumber,
            brandName: brand,
            modelName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
            forceRefresh: true,
          );
      final spec = fetchedAccessorySpecFromApi(raw);
      if (!mounted) return;
      setState(() {
        _fetching = false;
        if (spec.modelName.isNotEmpty) _modelName.text = spec.modelName;
        if ((spec.modelNumber ?? '').isNotEmpty) _modelNumber.text = spec.modelNumber!;
        if ((spec.partNumber ?? '').isNotEmpty) _partNumber.text = spec.partNumber!;
        _accessoryKind ??= spec.accessoryKind;
        if ((spec.colorOptions ?? '').isNotEmpty) _colorOptions.text = spec.colorOptions!;
        if ((spec.notes ?? '').isNotEmpty) _specNotes.text = spec.notes!;
        _productImageUrl = spec.productImageUrl;
        _specMessage = _accessoryKind == null
            ? 'Configuration fetched — select accessory type if auto-detect missed it.'
            : 'Configuration fetched — review and adjust if needed.';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _fetching = false;
        _specMessage = 'Auto-fetch failed — enter details manually.';
      });
    }
  }

  List<String> get _trimmedSerials =>
      _serials.map((c) => c.text.trim()).where((s) => s.isNotEmpty).toList();

  int get _duplicateCount =>
      _trimmedSerials.where((s) => _knownDuplicates.contains(s.toUpperCase())).length;

  bool get _hasEmptySerial => _serials.any((c) => c.text.trim().isEmpty);

  bool get _hasInternalDuplicates {
    final upper = _trimmedSerials.map((s) => s.toUpperCase()).toList();
    return upper.toSet().length != upper.length;
  }

  String _resolvedColor() {
    if (_mode == 'existing') {
      final model = _brandModels.where((m) => m.id == _selectedModelId).firstOrNull;
      return defaultUnitColorFromOptions(model?.colorOptions);
    }
    return defaultUnitColorFromOptions(
      _colorOptions.text.trim().isEmpty ? null : _colorOptions.text.trim(),
    );
  }

  bool get _canImport {
    if (_mode == null) return false;
    if (_trimmedSerials.isEmpty) return false;
    if (_hasEmptySerial || _duplicateCount > 0 || _hasInternalDuplicates) return false;
    if (_locationId <= 0) return false;
    if (_mode == 'new') {
      if (_modelNumber.text.trim().isEmpty || _modelName.text.trim().isEmpty) {
        return false;
      }
      if (_itemType == 'accessory') {
        if (_accessoryKind == null) return false;
      } else if (_cpu.text.trim().isEmpty) {
        return false;
      }
    }
    if (_mode == 'existing' && (_selectedModelId == null || _selectedModelId!.isEmpty)) {
      return false;
    }
    return true;
  }

  Map<String, dynamic> _buildNewModel() {
    if (_itemType == 'accessory') {
      final partNumber = _partNumber.text.trim();
      return {
        'brand_id': _brandId,
        'category': 'accessory',
        'accessory_kind': _accessoryKind == null ? null : accessoryKindToApi(_accessoryKind!),
        'part_number': partNumber.isEmpty ? null : partNumber,
        'model_number': _modelNumber.text.trim(),
        'model_name': _modelName.text.trim(),
        'color_options': _colorOptions.text.trim().isEmpty ? null : _colorOptions.text.trim(),
        'product_image_url': _productImageUrl,
        'notes': _specNotes.text.trim().isEmpty ? null : _specNotes.text.trim(),
      };
    }
    return {
      'brand_id': _brandId,
      'model_number': _modelNumber.text.trim(),
      'model_name': _modelName.text.trim(),
      'cpu': _cpu.text.trim(),
      'gpu': _gpu.text.trim().isEmpty ? null : _gpu.text.trim(),
      'ram_gb': int.tryParse(_ramGb.text.trim()) ?? 16,
      'storage_value': _storageValue.text.trim(),
      'storage_unit': _storageUnit,
      'storage_type': _storageType,
      'display': _display.text.trim().isEmpty ? null : _display.text.trim(),
      'color_options': _colorOptions.text.trim().isEmpty ? null : _colorOptions.text.trim(),
      'product_image_url': _productImageUrl,
      'notes': _specNotes.text.trim().isEmpty ? null : _specNotes.text.trim(),
    };
  }

  Future<void> _confirmAndImport() async {
    final brandName = _brands.where((b) => b.id == _brandId).map((b) => b.name).firstOrNull ?? '';
    final modelLabel = _mode == 'existing'
        ? (_brandModels.where((m) => m.id == _selectedModelId).map((m) => '${m.modelNumber} — ${m.modelName}').firstOrNull ?? '')
        : '${_modelNumber.text.trim()} — ${_modelName.text.trim()}';
    final locationName = _locations.where((l) => l.id == _locationId).map((l) => l.name).firstOrNull ?? '—';
    final serialCount = _trimmedSerials.length;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm import'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _ConfirmRow('Supplier', widget.voucher.supplierName ?? '—'),
              _ConfirmRow('Brand', brandName),
              _ConfirmRow('Model', modelLabel),
              _ConfirmRow('Existing model', _mode == 'existing' ? 'YES' : 'NO'),
              _ConfirmRow('Quantity', '$serialCount'),
              _ConfirmRow('Serial count', '$serialCount'),
              _ConfirmRow('Duplicate count', '$_duplicateCount'),
              const _ConfirmRow('Destination', 'Inventory (Tally Purchase)'),
              _ConfirmRow('Location', locationName),
              _ConfirmRow(
                'Purchase price',
                _purchasePrice.text.trim().isEmpty ? '—' : _purchasePrice.text.trim(),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirm import')),
        ],
      ),
    );
    if (confirmed != true) return;
    await _import();
  }

  Future<void> _import() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final price = _purchasePrice.text.trim();
      final request = PurchaseImportRequest(
        voucherId: widget.voucher.id,
        groupKey: widget.group.groupKey,
        brandId: _brandId,
        mode: _mode!,
        productModelId: _mode == 'existing' ? _selectedModelId : null,
        newProductModel: _mode == 'new' ? _buildNewModel() : null,
        serialNumbers: _trimmedSerials,
        color: _resolvedColor(),
        currentLocationId: _locationId,
        status: _status,
        purchasePrice: price.isEmpty ? null : double.tryParse(price),
      );
      await ref.read(purchaseRepositoryProvider).importGroup(request);
      if (!mounted) return;
      Navigator.pop(context);
      widget.onImported();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Imported ${request.serialNumbers.length} unit(s).')),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = formatApiError(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final viewInsets = MediaQuery.viewInsetsOf(context);
    final maxHeight = MediaQuery.sizeOf(context).height * 0.92;
    final sheetHeight = (maxHeight - viewInsets.bottom).clamp(320.0, maxHeight);

    return Material(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: sheetHeight,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(
                          AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.md),
                      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                      children: [
                        Center(
                          child: Container(
                            width: 40,
                            height: 4,
                            margin: const EdgeInsets.only(bottom: AppSpacing.md),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.outlineVariant,
                              borderRadius: BorderRadius.circular(99),
                            ),
                          ),
                        ),
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Import — ${widget.group.stockItemName}',
                                      style: theme.textTheme.titleLarge),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Supplier ${widget.voucher.supplierName ?? '—'} · '
                                    'Purchase ${widget.voucher.voucherNumber} · Qty ${widget.group.quantity}',
                                    style: theme.textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              onPressed: () => Navigator.pop(context),
                              icon: const Icon(Icons.close),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        ..._brandStep(theme),
                        if (_brandId > 0) ..._itemTypeStep(theme),
                        if (_brandId > 0 && _itemType.isNotEmpty) ..._modelStep(theme),
                        if (_mode != null) ..._detailStep(theme),
                        if (_error != null) ...[
                          const SizedBox(height: AppSpacing.md),
                          Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
                        ],
                      ],
                    ),
                  ),
                  Material(
                    elevation: 6,
                    color: theme.colorScheme.surface,
                    child: SafeArea(
                      top: false,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(
                            AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.md),
                        child: Row(
                          children: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('Cancel'),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: FilledButton(
                                onPressed: (!_canImport || _submitting) ? null : _confirmAndImport,
                                child: Text(_submitting ? 'Importing…' : 'Review & import'),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  List<Widget> _brandStep(ThemeData theme) {
    return [
      DropdownButtonFormField<int>(
        // ignore: deprecated_member_use
        value: _brandId == 0 ? null : _brandId,
        decoration: const InputDecoration(labelText: 'Brand'),
        items: _brands
            .map((brand) => DropdownMenuItem(value: brand.id, child: Text(brand.name)))
            .toList(),
        onChanged: _matching ? null : (value) => value == null ? null : _onBrandChanged(value),
      ),
      const SizedBox(height: AppSpacing.xs),
      Text('Brand determines which catalogue is searched.', style: theme.textTheme.bodySmall),
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _itemTypeStep(ThemeData theme) {
    return [
      Text('Item type', style: theme.textTheme.labelLarge),
      const SizedBox(height: AppSpacing.xs),
      Row(
        children: [
          Expanded(
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'laptop', label: Text('Laptop')),
                ButtonSegment(value: 'accessory', label: Text('Accessory')),
              ],
              selected: _itemType.isEmpty ? const <String>{} : {_itemType},
              emptySelectionAllowed: true,
              onSelectionChanged: _matching
                  ? null
                  : (selection) =>
                      selection.isEmpty ? null : _chooseItemType(selection.first),
            ),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.xs),
      Text(
        'Laptops match by serial/model. Accessories are searched by part number and model name.',
        style: theme.textTheme.bodySmall,
      ),
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _modelStep(ThemeData theme) {
    if (_matching) {
      return [
        const SizedBox(height: AppSpacing.sm),
        const LinearProgressIndicator(minHeight: 2),
        const SizedBox(height: AppSpacing.md),
      ];
    }
    if (_itemType == 'accessory') {
      return _accessoryMatchStep(theme);
    }
    final match = _match;
    return [
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _mode == 'new' ? '__new__' : _selectedModelId,
        decoration: const InputDecoration(labelText: 'Model'),
        items: [
          ...?match?.matches.map(
            (m) => DropdownMenuItem(
              value: m.id,
              enabled: m.isActive,
              child: Text(
                '${m.modelNumber} — ${m.modelName}'
                '${m.isPartial ? ' (possible match)' : ''}'
                '${m.isActive ? '' : ' (archived)'}',
              ),
            ),
          ),
          const DropdownMenuItem(value: '__new__', child: Text('+ Create new model')),
        ],
        onChanged: (value) {
          if (value == null) return;
          setState(() {
            _error = null;
            if (value == '__new__') {
              _mode = 'new';
              _selectedModelId = null;
              if (_modelNumber.text.trim().isEmpty) {
                _modelNumber.text = match?.normalizedModelNumber ??
                    stripBrandPrefixForSeed(widget.group.stockItemName, _brandName);
              }
              if (_modelName.text.trim().isEmpty) {
                _modelName.text = stripBrandPrefixForSeed(widget.group.stockItemName, _brandName);
              }
            } else {
              _mode = 'existing';
              _selectedModelId = value;
            }
          });
          if (value == '__new__' && _cpu.text.trim().isEmpty) {
            _runAutoFetch();
          }
        },
      ),
      if (match != null) ...[
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Normalized: ${match.normalizedModelNumber}. '
          '${match.autoSelectedModelId != null ? 'Existing model found — new serial numbers will be appended.' : match.matches.isEmpty ? 'No existing model matched — create a new model.' : match.matches.any((m) => m.isPartial) ? 'Possible match(es) found — select one, or create a new model if it is different.' : 'Select a model or create a new one.'}',
          style: theme.textTheme.bodySmall,
        ),
      ],
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _accessoryMatchStep(ThemeData theme) {
    final match = _accMatch;
    return [
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _mode == 'new' ? '__new__' : _selectedModelId,
        decoration: const InputDecoration(labelText: 'Accessory'),
        isExpanded: true,
        items: [
          ...?match?.matches.map(
            (m) => DropdownMenuItem(
              value: m.id,
              enabled: m.isActive,
              child: Text(
                '${m.modelNumber} — ${m.modelName}'
                '${m.partNumber != null ? ' · PN ${m.partNumber}' : ''}'
                ' (${(m.score * 100).round()}%)${m.isActive ? '' : ' (archived)'}',
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
          const DropdownMenuItem(value: '__new__', child: Text('+ Create new accessory')),
        ],
        onChanged: (value) {
          if (value == null) return;
          setState(() {
            _error = null;
            if (value == '__new__') {
              _mode = 'new';
              _selectedModelId = null;
              if (_modelNumber.text.trim().isEmpty) {
                _modelNumber.text = match?.normalizedQuery ??
                    stripBrandPrefixForSeed(widget.group.stockItemName, _brandName);
              }
              if (_modelName.text.trim().isEmpty) {
                _modelName.text = stripBrandPrefixForSeed(widget.group.stockItemName, _brandName);
              }
            } else {
              _mode = 'existing';
              _selectedModelId = value;
            }
          });
          if (value == '__new__' && _accessoryKind == null) {
            _runAccessoryAutoFetch();
          }
        },
      ),
      if (match != null) ...[
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Searched: ${match.normalizedQuery}. '
          '${match.autoSelectedModelId != null ? 'Matching accessory found — new serial numbers will be appended.' : match.matches.isEmpty ? 'No matching accessory found — create a new accessory.' : 'Select the closest accessory or create a new one.'}',
          style: theme.textTheme.bodySmall,
        ),
      ],
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _detailStep(ThemeData theme) {
    return [
      if (_mode == 'new')
        ...(_itemType == 'accessory' ? _accessorySpecFields(theme) : _specFields(theme)),
      Text('Serial numbers (${_trimmedSerials.length} / Qty ${widget.group.quantity})',
          style: theme.textTheme.labelLarge),
      const SizedBox(height: AppSpacing.xs),
      for (var i = 0; i < _serials.length; i++) ...[
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _serials[i],
                decoration: InputDecoration(
                  labelText: 'Serial ${i + 1}',
                  errorText: _knownDuplicates.contains(_serials[i].text.trim().toUpperCase())
                      ? 'Already in IMS'
                      : null,
                ),
                textCapitalization: TextCapitalization.characters,
                onChanged: (_) => setState(() => _error = null),
              ),
            ),
            IconButton(
              tooltip: 'Remove',
              onPressed: () => setState(() {
                _serials.removeAt(i).dispose();
                if (_serials.isEmpty) _serials.add(TextEditingController());
              }),
              icon: const Icon(Icons.delete_outline),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
      ],
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: () => setState(() => _serials.add(TextEditingController())),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Add serial'),
        ),
      ),
      if (_duplicateCount > 0)
        Text('$_duplicateCount serial(s) already exist in IMS — import blocked.',
            style: TextStyle(color: theme.colorScheme.error)),
      if (_hasInternalDuplicates)
        Text('The serial list contains repeated values.',
            style: TextStyle(color: theme.colorScheme.error)),
      const SizedBox(height: AppSpacing.md),
      DropdownButtonFormField<int>(
        // ignore: deprecated_member_use
        value: _locations.any((l) => l.id == _locationId) ? _locationId : null,
        decoration: const InputDecoration(labelText: 'Location (applied to all)'),
        items: _locations
            .map((l) => DropdownMenuItem(value: l.id, child: Text(l.name)))
            .toList(),
        onChanged: (value) => value == null ? null : setState(() => _locationId = value),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _purchasePrice,
        decoration: const InputDecoration(
          labelText: 'Purchase price (applied to all)',
          hintText: 'Optional',
        ),
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _status,
        decoration: const InputDecoration(labelText: 'Initial status'),
        items: const [
          DropdownMenuItem(value: 'received', child: Text('Received')),
          DropdownMenuItem(value: 'available', child: Text('Available')),
        ],
        onChanged: (value) => setState(() => _status = value ?? 'available'),
      ),
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _specFields(ThemeData theme) {
    return [
      Text('New model configuration', style: theme.textTheme.labelLarge),
      if (_specMessage != null) ...[
        const SizedBox(height: AppSpacing.xs),
        Text(_specMessage!, style: theme.textTheme.bodySmall),
      ],
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _modelNumber,
        decoration: const InputDecoration(labelText: 'Model number'),
        textCapitalization: TextCapitalization.characters,
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _modelName,
        decoration: const InputDecoration(labelText: 'Model name'),
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _cpu,
        decoration: const InputDecoration(labelText: 'CPU'),
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _gpu, decoration: const InputDecoration(labelText: 'GPU')),
      const SizedBox(height: AppSpacing.sm),
      Row(
        children: [
          Expanded(
            child: TextField(
              controller: _ramGb,
              decoration: const InputDecoration(labelText: 'RAM (GB)'),
              keyboardType: TextInputType.number,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _storageValue,
              decoration: const InputDecoration(labelText: 'Storage'),
            ),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.sm),
      Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              // ignore: deprecated_member_use
              value: _storageUnit,
              decoration: const InputDecoration(labelText: 'Storage unit'),
              items: const [
                DropdownMenuItem(value: 'GB', child: Text('GB')),
                DropdownMenuItem(value: 'TB', child: Text('TB')),
              ],
              onChanged: (value) => setState(() => _storageUnit = value ?? 'GB'),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: DropdownButtonFormField<String>(
              // ignore: deprecated_member_use
              value: _storageType,
              decoration: const InputDecoration(labelText: 'Storage type'),
              items: const [
                DropdownMenuItem(value: 'SSD', child: Text('SSD')),
                DropdownMenuItem(value: 'HDD', child: Text('HDD')),
              ],
              onChanged: (value) => setState(() => _storageType = value ?? 'SSD'),
            ),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _display, decoration: const InputDecoration(labelText: 'Display')),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _colorOptions,
        decoration: const InputDecoration(labelText: 'Color options'),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _specNotes,
        decoration: const InputDecoration(labelText: 'Additional specs'),
        maxLines: 2,
      ),
      if (_productImageUrl != null && _productImageUrl!.isNotEmpty) ...[
        const SizedBox(height: AppSpacing.sm),
        ProductModelImage(imageUrl: _productImageUrl!, height: 100),
      ],
      const SizedBox(height: AppSpacing.sm),
      SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: _fetching ? null : _runAutoFetch,
          child: Text(_fetching ? 'Fetching…' : 'Auto fetch configuration'),
        ),
      ),
      const SizedBox(height: AppSpacing.md),
    ];
  }

  List<Widget> _accessorySpecFields(ThemeData theme) {
    return [
      Text('New accessory configuration', style: theme.textTheme.labelLarge),
      if (_specMessage != null) ...[
        const SizedBox(height: AppSpacing.xs),
        Text(_specMessage!, style: theme.textTheme.bodySmall),
      ],
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _partNumber,
        decoration: const InputDecoration(
          labelText: 'Part number',
          hintText: 'Optional',
        ),
        textCapitalization: TextCapitalization.characters,
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _modelNumber,
        decoration: const InputDecoration(labelText: 'Model number'),
        textCapitalization: TextCapitalization.characters,
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _modelName,
        decoration: const InputDecoration(labelText: 'Model name'),
        onChanged: (_) => setState(() {}),
      ),
      const SizedBox(height: AppSpacing.sm),
      DropdownButtonFormField<AccessoryKind>(
        // ignore: deprecated_member_use
        value: _accessoryKind,
        decoration: const InputDecoration(labelText: 'Accessory type'),
        items: accessoryKindOptions
            .map((o) => DropdownMenuItem(value: o.value, child: Text(o.label)))
            .toList(),
        onChanged: (value) => setState(() => _accessoryKind = value),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _colorOptions,
        decoration: const InputDecoration(labelText: 'Color options'),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _specNotes,
        decoration: const InputDecoration(labelText: 'Additional details'),
        maxLines: 2,
      ),
      if (_productImageUrl != null && _productImageUrl!.isNotEmpty) ...[
        const SizedBox(height: AppSpacing.sm),
        ProductModelImage(imageUrl: _productImageUrl!, height: 100),
      ],
      const SizedBox(height: AppSpacing.sm),
      SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: _fetching ? null : _runAccessoryAutoFetch,
          child: Text(_fetching ? 'Fetching…' : 'Auto fetch configuration'),
        ),
      ),
      const SizedBox(height: AppSpacing.md),
    ];
  }
}

class _ConfirmRow extends StatelessWidget {
  const _ConfirmRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: Theme.of(context).textTheme.bodySmall),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}
