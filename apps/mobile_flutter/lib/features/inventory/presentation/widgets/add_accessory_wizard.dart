import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_exception.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../ai/data/ai_enrichment_repository.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../domain/accessory_spec_lookup.dart';
import '../../domain/barcode_field_resolver.dart';
import '../../domain/inventory_models.dart';
import '../../domain/inventory_permissions.dart' as inv_perms;
import '../../domain/product_category.dart';
import '../../domain/product_spec_lookup.dart';
import '../../../../core/device/barcode_scan_launcher.dart';
import '../inventory_controller.dart';

enum _WizardStep { model, specs, units, review }

Future<void> showAddAccessoryWizard(
  BuildContext context,
  WidgetRef ref, {
  required int brandId,
  required String brandName,
  required InventoryWorkspaceProvider workspaceProvider,
}) async {
  final workspace = ref.read(workspaceProvider);
  if (workspace.locations.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Load locations before adding inventory.')),
    );
    return;
  }

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: _AddAccessoryWizard(
        brandId: brandId,
        brandName: brandName,
        models: workspace.models.where((model) => model.brandId == brandId).toList(),
        locations: workspace.locations,
        workspaceProvider: workspaceProvider,
      ),
    ),
  );
}

class _AddAccessoryWizard extends ConsumerStatefulWidget {
  const _AddAccessoryWizard({
    required this.brandId,
    required this.brandName,
    required this.models,
    required this.locations,
    required this.workspaceProvider,
  });

  final int brandId;
  final String brandName;
  final List<ProductModel> models;
  final List<Location> locations;
  final InventoryWorkspaceProvider workspaceProvider;

  @override
  ConsumerState<_AddAccessoryWizard> createState() => _AddAccessoryWizardState();
}

class _AddAccessoryWizardState extends ConsumerState<_AddAccessoryWizard> {
  _WizardStep _step = _WizardStep.model;
  String _mode = 'new';
  String? _productModelId;
  ProductModel? _existingModel;
  int _existingAvailableUnits = 0;

  AccessoryIdentifierType _identifierType = AccessoryIdentifierType.partNumber;
  final _identifier = TextEditingController();
  final _identifierFocus = FocusNode();
  final _modelName = TextEditingController();
  final _resolvedModelNumber = TextEditingController();
  final _resolvedPartNumber = TextEditingController();
  final _colorOptions = TextEditingController();
  final _description = TextEditingController();
  final _specNotes = TextEditingController();

  AccessoryKind? _accessoryKind;
  String? _productImageUrl;
  int _unitCount = 1;
  final List<_UnitRow> _units = [];

  bool _checking = false;
  bool _fetching = false;
  bool _submitting = false;
  String? _message;
  String? _error;

  @override
  void initState() {
    super.initState();
    _resetUnits();
    _identifier.addListener(_onFormChanged);
    _modelName.addListener(_onFormChanged);
    _resolvedModelNumber.addListener(_onFormChanged);
    _resolvedPartNumber.addListener(_onFormChanged);
  }

  void _onFormChanged() {
    if (!mounted) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() {});
    });
  }

  void _attachUnitListeners() {
    for (final row in _units) {
      row.serial.removeListener(_onFormChanged);
      row.serial.addListener(_onFormChanged);
      row.purchasePrice.removeListener(_onFormChanged);
      row.purchasePrice.addListener(_onFormChanged);
    }
  }

  @override
  void dispose() {
    _identifier.removeListener(_onFormChanged);
    _modelName.removeListener(_onFormChanged);
    _resolvedModelNumber.removeListener(_onFormChanged);
    _resolvedPartNumber.removeListener(_onFormChanged);
    for (final row in _units) {
      row.serial.removeListener(_onFormChanged);
      row.purchasePrice.removeListener(_onFormChanged);
      row.dispose();
    }
    _identifier.dispose();
    _identifierFocus.dispose();
    _modelName.dispose();
    _resolvedModelNumber.dispose();
    _resolvedPartNumber.dispose();
    _colorOptions.dispose();
    _description.dispose();
    _specNotes.dispose();
    super.dispose();
  }

  void _resetUnits() {
    final defaultLocation = widget.locations.isNotEmpty ? widget.locations.first.id : 0;
    for (final row in _units) {
      row.serial.removeListener(_onFormChanged);
      row.purchasePrice.removeListener(_onFormChanged);
      row.dispose();
    }
    _units
      ..clear()
      ..add(_UnitRow(serial: TextEditingController(), locationId: defaultLocation));
    _attachUnitListeners();
  }

  String _stepLabel() {
    if (_mode == 'existing') {
      return _step == _WizardStep.model ? '1 of 2' : '2 of 2';
    }
    return switch (_step) {
      _WizardStep.model => '1 of 4',
      _WizardStep.specs => '2 of 4',
      _WizardStep.units => '3 of 4',
      _WizardStep.review => '4 of 4',
    };
  }

  void _applyAccessorySpec(FetchedAccessorySpec spec) {
    if (spec.modelName.isNotEmpty) _modelName.text = spec.modelName;
    _resolvedModelNumber.text = spec.modelNumber ?? '';
    _resolvedPartNumber.text = spec.partNumber ?? '';
    _accessoryKind = spec.accessoryKind;
    _colorOptions.text = spec.colorOptions ?? '';
    if (spec.description != null && spec.description!.isNotEmpty) {
      _description.text = spec.description!;
    }
    _specNotes.text = spec.notes ?? '';
    _productImageUrl = spec.productImageUrl;
  }

  void _applyExistingModel(ProductModel model) {
    _mode = 'existing';
    _productModelId = model.id;
    _existingModel = model;
    _applyAccessorySpec(accessoryToDisplaySpec(model));
    _existingAvailableUnits =
        ref.read(widget.workspaceProvider.notifier).availableUnitsForModel(model.id);
  }

  Future<void> _continueFromModel() async {
    final trimmed = _identifier.text.trim();
    if (trimmed.isEmpty) return;

    setState(() {
      _checking = true;
      _error = null;
      _message = null;
    });

    final existing = findAccessoryByIdentifier(widget.models, trimmed, brandId: widget.brandId);
    if (existing != null) {
      _applyExistingModel(existing);
      setState(() {
        _checking = false;
        _step = _WizardStep.units;
        _message = _existingAvailableUnits > 0
            ? 'Accessory found — $_existingAvailableUnits unit(s) already in stock. Add more serial numbers below.'
            : 'Accessory found — add serial numbers to restore stock for this model.';
      });
      return;
    }

    setState(() {
      _mode = 'new';
      _productModelId = null;
      _existingModel = null;
      _accessoryKind = null;
      _modelName.clear();
      _resolvedModelNumber.clear();
      _resolvedPartNumber.clear();
      _colorOptions.clear();
      _description.clear();
      _specNotes.clear();
      _productImageUrl = null;
      _checking = false;
      _step = _WizardStep.specs;
    });
    await _runAutoFetch();
  }

  Future<void> _runAutoFetch({bool forceRefresh = false}) async {
    final trimmed = _identifier.text.trim();
    if (trimmed.isEmpty) return;
    setState(() {
      _fetching = true;
      _error = null;
      _message = null;
    });
    try {
      final spec = await fetchAccessorySpecFromInternet(
        () async {
          final raw = await ref.read(aiEnrichmentRepositoryProvider).lookupAccessorySpec(
                identifier: trimmed,
                identifierType: _identifierType,
                brandName: widget.brandName,
                modelName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
                forceRefresh: forceRefresh,
              );
          if ((raw['model_name'] as String?)?.trim().isEmpty ?? true) return null;
          return fetchedAccessorySpecFromApi(raw);
        },
        identifier: trimmed,
        identifierType: _identifierType,
        brandName: widget.brandName,
        forceRefresh: forceRefresh,
      );
      if (spec == null || spec.modelName.trim().isEmpty) {
        setState(() {
          _fetching = false;
          _message = 'Auto-fetch found no match — enter details manually or tap Auto fetch to retry.';
        });
        return;
      }
      _applyAccessorySpec(spec);
      setState(() {
        _fetching = false;
        _message = spec.accessoryKind == null
            ? (forceRefresh
                ? 'Configuration re-fetched — select accessory type manually if needed.'
                : 'Configuration partially fetched — select accessory type manually if needed.')
            : (forceRefresh
                ? 'Configuration re-fetched — review and adjust if needed.'
                : 'Configuration auto-fetched — review and adjust if needed.');
      });
    } catch (_) {
      setState(() {
        _fetching = false;
        _message = 'Auto-fetch failed — enter details manually or tap Auto fetch to retry.';
      });
    }
  }

  void _syncUnitRows(int count) {
    final clamped = count.clamp(1, 50);
    final defaultLocation = widget.locations.isNotEmpty ? widget.locations.first.id : 0;
    while (_units.length > clamped) {
      final removed = _units.removeLast();
      removed.serial.removeListener(_onFormChanged);
      removed.purchasePrice.removeListener(_onFormChanged);
      removed.dispose();
    }
    while (_units.length < clamped) {
      _units.add(_UnitRow(serial: TextEditingController(), locationId: defaultLocation));
    }
    _attachUnitListeners();
  }

  String _defaultUnitColor() {
    final source = _mode == 'existing'
        ? _existingModel?.colorOptions
        : (_colorOptions.text.trim().isEmpty ? null : _colorOptions.text.trim());
    return defaultUnitColorFromOptions(source);
  }

  List<SerialUnitEntry> _validUnits() {
    final color = _defaultUnitColor();
    return _units
        .where((row) => row.serial.text.trim().isNotEmpty && row.locationId > 0)
        .map(
          (row) {
            final priceRaw = row.purchasePrice.text.trim();
            return SerialUnitEntry(
              serialNumber: row.serial.text.trim(),
              color: color,
              currentLocationId: row.locationId,
              purchasePrice: priceRaw.isEmpty ? null : double.tryParse(priceRaw),
            );
          },
        )
        .toList();
  }

  void _applyFirstLocationToAll() {
    if (_units.isEmpty) return;
    final first = _units.first.locationId;
    setState(() {
      for (final row in _units) {
        row.locationId = first;
      }
    });
  }

  void _applyFirstPurchasePriceToAll() {
    if (_units.isEmpty) return;
    final first = _units.first.purchasePrice.text;
    setState(() {
      for (final row in _units) {
        row.purchasePrice.text = first;
      }
    });
  }

  Future<void> _submit() async {
    final units = _validUnits();
    if (units.isEmpty) {
      setState(() => _error = 'Enter at least one serial number and location.');
      return;
    }

    if (_mode == 'existing' && (_productModelId == null || _productModelId!.isEmpty)) {
      setState(() => _error = 'Select or resolve a product model.');
      return;
    }

    if (_mode == 'new') {
      if (_modelName.text.trim().isEmpty) {
        setState(() => _error = 'Model name is required.');
        return;
      }
      if (_accessoryKind == null) {
        setState(() => _error = 'Accessory type is required — use Auto fetch or pick a type manually.');
        return;
      }
    }

    for (final unit in units) {
      final duplicate = await ref.read(widget.workspaceProvider.notifier).checkSerialDuplicate(unit.serialNumber);
      if (duplicate) {
        setState(() => _error = 'Serial already exists: ${unit.serialNumber}');
        return;
      }
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final entered = _identifier.text.trim();
      final catalogPartNumber = _identifierType == AccessoryIdentifierType.partNumber
          ? (_resolvedPartNumber.text.trim().isEmpty ? entered : _resolvedPartNumber.text.trim())
          : (_resolvedPartNumber.text.trim().isEmpty ? null : _resolvedPartNumber.text.trim());
      final catalogModelNumber = _resolvedModelNumber.text.trim().isEmpty
          ? (_identifierType == AccessoryIdentifierType.modelNumber ? entered : (catalogPartNumber ?? entered))
          : _resolvedModelNumber.text.trim();

      final ok = await ref.read(widget.workspaceProvider.notifier).addLaptopWizard(
            AddLaptopWizardRequest(
              brandId: widget.brandId,
              mode: _mode,
              productModelId: _mode == 'existing' ? _productModelId : null,
              newProductModel: _mode == 'new'
                  ? {
                      'brand_id': widget.brandId,
                      'category': 'accessory',
                      'accessory_kind': accessoryKindToApi(_accessoryKind!),
                      'part_number': catalogPartNumber,
                      'model_number': catalogModelNumber,
                      'model_name': _modelName.text.trim(),
                      'color_options': _colorOptions.text.trim().isEmpty ? null : _colorOptions.text.trim(),
                      'product_image_url': _productImageUrl,
                      'notes': composeModelNotes(
                        _description.text.trim().isEmpty ? null : _description.text.trim(),
                        _specNotes.text.trim().isEmpty ? null : _specNotes.text.trim(),
                      ),
                    }
                  : null,
              units: units,
            ),
          );
      if (!mounted) return;
      if (!ok) {
        setState(() {
          _submitting = false;
          _error = ref.read(widget.workspaceProvider).error ?? 'Could not save accessory.';
        });
        return;
      }
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Added ${units.length} accessory unit(s) to ${widget.brandName}.')),
      );
    } catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _error = formatApiError(error);
        });
      }
    }
  }

  Future<void> _scanIdentifier() async {
    final scan = await openBarcodeScanner(
      context,
      ref,
      preferredTarget: _identifierType == AccessoryIdentifierType.partNumber
          ? BarcodeFieldTarget.partNumber
          : BarcodeFieldTarget.modelNumber,
    );
    if (scan == null || !mounted) return;
    setState(() {
      _identifier.text = scan.rawValue;
      _error = null;
    });
  }

  Future<void> _scanSerial(int index) async {
    final scan = await openBarcodeScanner(
      context,
      ref,
      preferredTarget: BarcodeFieldTarget.serialNumber,
    );
    if (scan == null || !mounted) return;
    setState(() {
      _units[index].serial.text = scan.rawValue;
      _error = scan.targetField == BarcodeFieldTarget.serialNumber
          ? null
          : 'Scanned as ${scan.targetField.label}. Value applied — verify before continuing.';
    });
  }

  int _resolvedLocationId(int locationId) {
    if (widget.locations.isEmpty) return locationId;
    if (widget.locations.any((location) => location.id == locationId)) return locationId;
    return widget.locations.first.id;
  }

  @override
  Widget build(BuildContext context) {
    final permissions = ref.watch(authControllerProvider).user?.permissions ?? const [];
    if (!inv_perms.canCreateInventory(permissions)) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Text('You do not have permission to add inventory.'),
      );
    }

    final viewInsets = MediaQuery.viewInsetsOf(context);
    final maxHeight = MediaQuery.sizeOf(context).height * 0.9;
    final sheetHeight = (maxHeight - viewInsets.bottom).clamp(280.0, maxHeight);

    return Material(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: sheetHeight,
        child: Column(
          children: [
            Expanded(
              child: ListView(
                key: ValueKey(_step),
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.md),
                keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                children: [
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: AppSpacing.md),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.outlineVariant,
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
                            Text('Add accessory — ${widget.brandName}', style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 4),
                            Text(
                              'Brand is fixed to ${widget.brandName}. Step ${_stepLabel()}.',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ..._stepBody(context),
                ],
              ),
            ),
            Material(
              elevation: 6,
              color: Theme.of(context).colorScheme.surface,
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, AppSpacing.md),
                  child: _stepActions(context),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _stepBody(BuildContext context) {
    return switch (_step) {
      _WizardStep.model => _modelStepBody(context),
      _WizardStep.specs => _specsStepBody(context),
      _WizardStep.units => _unitsStepBody(context),
      _WizardStep.review => _reviewStepBody(context),
    };
  }

  Widget _stepActions(BuildContext context) {
    return switch (_step) {
      _WizardStep.model => _modelStepActions(context),
      _WizardStep.specs => _specsStepActions(context),
      _WizardStep.units => _unitsStepActions(context),
      _WizardStep.review => _reviewStepActions(context),
    };
  }

  List<Widget> _modelStepBody(BuildContext context) {
    final canContinue = _identifier.text.trim().isNotEmpty;
    return [
      Text('Look up by', style: Theme.of(context).textTheme.labelLarge),
      const SizedBox(height: AppSpacing.xs),
      SegmentedButton<AccessoryIdentifierType>(
        segments: const [
          ButtonSegment(value: AccessoryIdentifierType.partNumber, label: Text('Part number')),
          ButtonSegment(value: AccessoryIdentifierType.modelNumber, label: Text('Model number')),
        ],
        selected: {_identifierType},
        onSelectionChanged: (selection) {
          setState(() {
            _identifierType = selection.first;
            _error = null;
          });
        },
      ),
      const SizedBox(height: AppSpacing.md),
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: TextField(
              controller: _identifier,
              focusNode: _identifierFocus,
              decoration: InputDecoration(
                labelText: identifierTypeLabel(_identifierType),
                hintText: _identifierType == AccessoryIdentifierType.partNumber
                    ? 'e.g. 90XB09VN-BPW000'
                    : 'e.g. MD102',
              ),
              keyboardType: TextInputType.visiblePassword,
              textCapitalization: TextCapitalization.characters,
              autocorrect: false,
              enableSuggestions: false,
              textInputAction: TextInputAction.done,
              onTap: () => _identifierFocus.requestFocus(),
              onChanged: (_) => setState(() => _error = null),
              onSubmitted: (_) {
                if (!_checking && canContinue) _continueFromModel();
              },
            ),
          ),
          IconButton(
            tooltip: 'Scan barcode',
            onPressed: _checking ? null : _scanIdentifier,
            icon: const Icon(Icons.qr_code_scanner),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.sm),
      Text(
        'Type or scan the ${identifierTypeLabel(_identifierType).toLowerCase()}. We check the database automatically — existing models skip configuration.',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      if (_error != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ],
      if (_message != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Text(_message!, style: Theme.of(context).textTheme.bodySmall),
      ],
    ];
  }

  Widget _modelStepActions(BuildContext context) {
    final canContinue = _identifier.text.trim().isNotEmpty;
    return Row(
      children: [
        Expanded(
          child: FilledButton(
            onPressed: _checking || !canContinue ? null : _continueFromModel,
            child: Text(_checking ? 'Checking database…' : 'Continue'),
          ),
        ),
      ],
    );
  }

  Widget _footerNavRow({
    required VoidCallback? onBack,
    required VoidCallback? onPrimary,
    required String primaryLabel,
    String backLabel = 'Back',
  }) {
    return Row(
      children: [
        TextButton(onPressed: onBack, child: Text(backLabel)),
        const SizedBox(width: 12),
        Expanded(
          child: FilledButton(
            onPressed: onPrimary,
            child: Text(primaryLabel),
          ),
        ),
      ],
    );
  }

  List<Widget> _specsStepBody(BuildContext context) {
    return [
      Text(
        'New accessory ${_identifier.text.trim()}'
        '${_fetching ? ' — auto-fetching configuration…' : ' — confirm or edit configuration below.'}',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      if (_message != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Text(_message!, style: Theme.of(context).textTheme.bodySmall),
      ],
      const SizedBox(height: AppSpacing.md),
      DropdownButtonFormField<AccessoryKind>(
        // ignore: deprecated_member_use
        value: _accessoryKind,
        decoration: const InputDecoration(labelText: 'Accessory type'),
        items: accessoryKindOptions
            .map(
              (option) => DropdownMenuItem(
                value: option.value,
                child: Text(option.label),
              ),
            )
            .toList(),
        onChanged: (value) => setState(() => _accessoryKind = value),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _modelName, decoration: const InputDecoration(labelText: 'Model name')),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _resolvedModelNumber,
        decoration: const InputDecoration(labelText: 'Model number'),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _resolvedPartNumber,
        decoration: const InputDecoration(labelText: 'Part number'),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _colorOptions, decoration: const InputDecoration(labelText: 'Colour / variant')),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _specNotes,
        decoration: const InputDecoration(labelText: 'Additional notes'),
        maxLines: 3,
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _description,
        decoration: const InputDecoration(labelText: 'Product description'),
        maxLines: 3,
      ),
      if (_productImageUrl != null && _productImageUrl!.isNotEmpty) ...[
        const SizedBox(height: AppSpacing.sm),
        ProductModelImage(imageUrl: _productImageUrl!, height: 100),
      ],
      const SizedBox(height: AppSpacing.md),
      SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: _fetching ? null : () => _runAutoFetch(forceRefresh: true),
          child: Text(_fetching ? 'Fetching…' : 'Auto fetch'),
        ),
      ),
    ];
  }

  Widget _specsStepActions(BuildContext context) {
    final canAdvance = _modelName.text.trim().isNotEmpty && _accessoryKind != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!canAdvance)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              'Enter model name and accessory type to continue.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
        _footerNavRow(
          onBack: () => setState(() => _step = _WizardStep.model),
          onPrimary: canAdvance ? () => setState(() => _step = _WizardStep.units) : null,
          primaryLabel: 'Next',
        ),
      ],
    );
  }

  List<Widget> _unitsStepBody(BuildContext context) {
    return [
      if (_mode == 'existing' && _existingModel != null) ...[
        Card(
          child: ListTile(
            title: Text(_existingModel!.modelNumber),
            subtitle: Text(
              '${_existingModel!.modelName}\n${_existingModel!.specsLabel}\n$_existingAvailableUnits unit(s) in stock',
            ),
            isThreeLine: true,
          ),
        ),
        if (_message != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(_message!, style: Theme.of(context).textTheme.bodySmall),
        ],
        const SizedBox(height: AppSpacing.md),
      ],
      Row(
        children: [
          Text('Number of units', style: Theme.of(context).textTheme.labelLarge),
          const Spacer(),
          IconButton(
            onPressed: _unitCount > 1
                ? () => setState(() {
                      _unitCount -= 1;
                      _syncUnitRows(_unitCount);
                    })
                : null,
            icon: const Icon(Icons.remove_circle_outline),
          ),
          Text('$_unitCount', style: Theme.of(context).textTheme.titleMedium),
          IconButton(
            onPressed: _unitCount < 50
                ? () => setState(() {
                      _unitCount += 1;
                      _syncUnitRows(_unitCount);
                    })
                : null,
            icon: const Icon(Icons.add_circle_outline),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.md),
      if (_units.length > 1) ...[
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            OutlinedButton(
              onPressed: _applyFirstLocationToAll,
              child: const Text('Apply first location to all'),
            ),
            OutlinedButton(
              onPressed: _units.first.purchasePrice.text.trim().isEmpty
                  ? null
                  : _applyFirstPurchasePriceToAll,
              child: const Text('Apply first purchase price to all'),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
      ],
      for (var i = 0; i < _units.length; i++) ...[
        Text('Unit ${i + 1}', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: AppSpacing.xs),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _units[i].serial,
                decoration: const InputDecoration(
                  labelText: 'Serial',
                  hintText: 'Type or scan barcode',
                ),
                onChanged: (_) => setState(() => _error = null),
              ),
            ),
            IconButton(
              tooltip: 'Scan serial',
              onPressed: () => _scanSerial(i),
              icon: const Icon(Icons.qr_code_scanner),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        DropdownButtonFormField<int>(
          // ignore: deprecated_member_use
          value: _resolvedLocationId(_units[i].locationId),
          decoration: const InputDecoration(labelText: 'Location'),
          items: widget.locations
              .map((location) => DropdownMenuItem(value: location.id, child: Text(location.name)))
              .toList(),
          onChanged: (value) {
            if (value == null) return;
            setState(() => _units[i].locationId = value);
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _units[i].purchasePrice,
          decoration: const InputDecoration(
            labelText: 'Purchase price',
            hintText: 'Optional',
          ),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.md),
      ],
      if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
    ];
  }

  Widget _unitsStepActions(BuildContext context) {
    return _footerNavRow(
      onBack: () => setState(
        () => _step = _mode == 'existing' ? _WizardStep.model : _WizardStep.specs,
      ),
      onPrimary: _mode == 'existing'
          ? (_submitting ? null : _submit)
          : () => setState(() => _step = _WizardStep.review),
      primaryLabel: _mode == 'existing'
          ? (_submitting ? 'Adding…' : 'Add to inventory')
          : 'Review',
    );
  }

  List<Widget> _reviewStepBody(BuildContext context) {
    final label = _modelName.text.trim().isEmpty ? _identifier.text.trim() : _modelName.text.trim();
    return [
      Text(label, style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: AppSpacing.sm),
      Text(
        '${_validUnits().length} unit(s) · ${accessoryKindLabel(_accessoryKind)} · New accessory',
      ),
      const SizedBox(height: AppSpacing.md),
      for (final unit in _validUnits())
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(unit.serialNumber),
          subtitle: Text(
            '${unit.color} · ${widget.locations.where((l) => l.id == unit.currentLocationId).map((l) => l.name).firstOrNull ?? '—'}',
          ),
        ),
      if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
    ];
  }

  Widget _reviewStepActions(BuildContext context) {
    return _footerNavRow(
      onBack: () => setState(() => _step = _WizardStep.units),
      onPrimary: _submitting ? null : _submit,
      primaryLabel: _submitting ? 'Adding…' : 'Add to inventory',
    );
  }
}

class _UnitRow {
  _UnitRow({
    required this.serial,
    required this.locationId,
    TextEditingController? purchasePrice,
  }) : purchasePrice = purchasePrice ?? TextEditingController();

  final TextEditingController serial;
  final TextEditingController purchasePrice;
  int locationId;

  void dispose() {
    serial.dispose();
    purchasePrice.dispose();
  }
}
