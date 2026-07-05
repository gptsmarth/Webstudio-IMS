import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../ai/data/ai_enrichment_repository.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../domain/inventory_models.dart';
import '../../domain/inventory_permissions.dart' as inv_perms;
import '../../domain/product_spec_lookup.dart';
import '../../../../core/device/barcode_scan_launcher.dart';
import '../../domain/barcode_field_resolver.dart';
import '../inventory_controller.dart';

enum _WizardStep { model, specs, units, review }

Future<void> showAddLaptopWizard(
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
      child: _AddLaptopWizard(
        brandId: brandId,
        brandName: brandName,
        models: workspace.models.where((model) => model.brandId == brandId).toList(),
        locations: workspace.locations,
        workspaceProvider: workspaceProvider,
      ),
    ),
  );
}

class _AddLaptopWizard extends ConsumerStatefulWidget {
  const _AddLaptopWizard({
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
  ConsumerState<_AddLaptopWizard> createState() => _AddLaptopWizardState();
}

class _AddLaptopWizardState extends ConsumerState<_AddLaptopWizard> {
  _WizardStep _step = _WizardStep.model;
  String _mode = 'new';
  String? _productModelId;
  ProductModel? _existingModel;
  int _existingAvailableUnits = 0;

  final _modelNumber = TextEditingController();
  final _modelNumberFocus = FocusNode();
  final _modelName = TextEditingController();
  final _cpu = TextEditingController();
  final _gpu = TextEditingController();
  final _ramGb = TextEditingController(text: '16');
  final _storageValue = TextEditingController(text: '512');
  final _display = TextEditingController();
  final _colorOptions = TextEditingController();
  final _description = TextEditingController();
  final _specNotes = TextEditingController();

  String _storageUnit = 'GB';
  String _storageType = 'SSD';
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
    _modelNumber.addListener(_onFormChanged);
    _modelName.addListener(_onFormChanged);
    _cpu.addListener(_onFormChanged);
    _gpu.addListener(_onFormChanged);
    _ramGb.addListener(_onFormChanged);
    _storageValue.addListener(_onFormChanged);
    _display.addListener(_onFormChanged);
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
    }
  }

  @override
  void dispose() {
    _modelNumber.removeListener(_onFormChanged);
    _modelName.removeListener(_onFormChanged);
    _cpu.removeListener(_onFormChanged);
    _gpu.removeListener(_onFormChanged);
    _ramGb.removeListener(_onFormChanged);
    _storageValue.removeListener(_onFormChanged);
    _display.removeListener(_onFormChanged);
    for (final row in _units) {
      row.serial.removeListener(_onFormChanged);
      row.dispose();
    }
    _modelNumber.dispose();
    _modelNumberFocus.dispose();
    _modelName.dispose();
    _cpu.dispose();
    _gpu.dispose();
    _ramGb.dispose();
    _storageValue.dispose();
    _display.dispose();
    _colorOptions.dispose();
    _description.dispose();
    _specNotes.dispose();
    super.dispose();
  }

  void _resetUnits() {
    final defaultLocation = widget.locations.isNotEmpty ? widget.locations.first.id : 0;
    for (final row in _units) {
      row.serial.removeListener(_onFormChanged);
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

  void _applySpec(FetchedProductSpec spec) {
    if (spec.modelName.isNotEmpty) _modelName.text = spec.modelName;
    _cpu.text = spec.cpu;
    _gpu.text = spec.gpu ?? '';
    _ramGb.text = '${spec.ramGb}';
    _storageValue.text = spec.storageValue;
    _storageUnit = spec.storageUnit == 'TB' ? 'TB' : 'GB';
    _storageType = spec.storageType == 'HDD' ? 'HDD' : 'SSD';
    _display.text = spec.display ?? '';
    _colorOptions.text = spec.colorOptions ?? '';
    _description.text = spec.description ?? '';
    _specNotes.text = spec.notes ?? '';
    _productImageUrl = spec.productImageUrl;
  }

  void _applyExistingModel(ProductModel model) {
    _mode = 'existing';
    _productModelId = model.id;
    _existingModel = model;
    _modelNumber.text = model.modelNumber;
    _modelName.text = model.modelName;
    _applySpec(FetchedProductSpec.fromProductModel(model));
    _existingAvailableUnits =
        ref.read(widget.workspaceProvider.notifier).availableUnitsForModel(model.id);
  }

  Future<void> _continueFromModel() async {
    final trimmed = _modelNumber.text.trim();
    if (trimmed.isEmpty) return;

    setState(() {
      _checking = true;
      _error = null;
      _message = null;
    });

    final existing = findModelByNumber(
      widget.models.where((model) => model.isLaptop).toList(),
      trimmed,
      brandId: widget.brandId,
    );
    if (existing != null) {
      _applyExistingModel(existing);
      setState(() {
        _checking = false;
        _step = _WizardStep.units;
        _message = _existingAvailableUnits > 0
            ? 'Model found — $_existingAvailableUnits unit(s) already in stock. Add more serial numbers below.'
            : 'Model found — add serial numbers to restore stock for this model.';
      });
      return;
    }

    setState(() {
      _mode = 'new';
      _productModelId = null;
      _existingModel = null;
      _checking = false;
      _step = _WizardStep.specs;
    });
    await _runAutoFetch();
  }

  Future<void> _runAutoFetch() async {
    final trimmed = _modelNumber.text.trim();
    if (trimmed.isEmpty) return;
    setState(() {
      _fetching = true;
      _error = null;
      _message = null;
    });
    try {
      final raw = await ref.read(aiEnrichmentRepositoryProvider).lookupSpecs(
            brandName: widget.brandName,
            modelNumber: trimmed,
            modelName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
          );
      final spec = FetchedProductSpec.fromApi(raw);
      if (spec.cpu.trim().isEmpty) {
        setState(() {
          _fetching = false;
          _message = 'Auto-fetch found no match — enter details manually or tap Auto fetch to retry.';
        });
        return;
      }
      _applySpec(spec);
      setState(() {
        _fetching = false;
        _message = 'Configuration auto-fetched — review and adjust if needed.';
      });
    } catch (error) {
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
      removed.dispose();
    }
    while (_units.length < clamped) {
      _units.add(
        _UnitRow(
          serial: TextEditingController(),
          locationId: defaultLocation,
        ),
      );
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
          (row) => SerialUnitEntry(
            serialNumber: row.serial.text.trim(),
            color: color,
            currentLocationId: row.locationId,
          ),
        )
        .toList();
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
      if (_modelNumber.text.trim().isEmpty || _modelName.text.trim().isEmpty || _cpu.text.trim().isEmpty) {
        setState(() => _error = 'Model number, name, and CPU are required.');
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
      await ref.read(widget.workspaceProvider.notifier).addLaptopWizard(
            AddLaptopWizardRequest(
              brandId: widget.brandId,
              mode: _mode,
              productModelId: _mode == 'existing' ? _productModelId : null,
              newProductModel: _mode == 'new'
                  ? {
                      'brand_id': widget.brandId,
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
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Added ${units.length} unit(s) to ${widget.brandName}.')),
      );
    } catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _error = error.toString();
        });
      }
    }
  }

  Future<void> _scanModelNumber() async {
    final scan = await openBarcodeScanner(
      context,
      ref,
      preferredTarget: BarcodeFieldTarget.modelNumber,
    );
    if (scan == null || !mounted) return;
    setState(() {
      _modelNumber.text = scan.rawValue;
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
                            Text('Add laptop — ${widget.brandName}', style: Theme.of(context).textTheme.titleLarge),
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

  int _resolvedLocationId(int locationId) {
    if (widget.locations.isEmpty) return locationId;
    if (widget.locations.any((location) => location.id == locationId)) return locationId;
    return widget.locations.first.id;
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
    final canContinue = _modelNumber.text.trim().isNotEmpty;
    return [
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: TextField(
              controller: _modelNumber,
              focusNode: _modelNumberFocus,
              decoration: const InputDecoration(
                labelText: 'Model number',
                hintText: 'e.g. X151VA-AB5321WS',
              ),
              keyboardType: TextInputType.visiblePassword,
              textCapitalization: TextCapitalization.characters,
              autocorrect: false,
              enableSuggestions: false,
              textInputAction: TextInputAction.done,
              onTap: () => _modelNumberFocus.requestFocus(),
              onChanged: (_) => setState(() => _error = null),
              onSubmitted: (_) {
                if (!_checking && canContinue) _continueFromModel();
              },
            ),
          ),
          IconButton(
            tooltip: 'Scan model barcode',
            onPressed: _checking ? null : _scanModelNumber,
            icon: const Icon(Icons.qr_code_scanner),
          ),
        ],
      ),
      const SizedBox(height: AppSpacing.sm),
      Text(
        'Type or scan the model number. We check the database automatically — existing models skip configuration.',
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
    final canContinue = _modelNumber.text.trim().isNotEmpty;
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
        'New model ${_modelNumber.text.trim()}'
        '${_fetching ? ' — auto-fetching configuration…' : ' — confirm or edit configuration below.'}',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      if (_message != null) ...[
        const SizedBox(height: AppSpacing.sm),
        Text(_message!, style: Theme.of(context).textTheme.bodySmall),
      ],
      const SizedBox(height: AppSpacing.md),
      TextField(controller: _modelName, decoration: const InputDecoration(labelText: 'Model name')),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _cpu, decoration: const InputDecoration(labelText: 'CPU')),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _gpu, decoration: const InputDecoration(labelText: 'GPU')),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _ramGb,
        decoration: const InputDecoration(labelText: 'RAM (GB)'),
        keyboardType: TextInputType.number,
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _storageValue, decoration: const InputDecoration(labelText: 'Storage')),
      const SizedBox(height: AppSpacing.sm),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _storageUnit,
        decoration: const InputDecoration(labelText: 'Storage unit'),
        items: const [
          DropdownMenuItem(value: 'GB', child: Text('GB')),
          DropdownMenuItem(value: 'TB', child: Text('TB')),
        ],
        onChanged: (value) => setState(() => _storageUnit = value ?? 'GB'),
      ),
      const SizedBox(height: AppSpacing.sm),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _storageType,
        decoration: const InputDecoration(labelText: 'Storage type'),
        items: const [
          DropdownMenuItem(value: 'SSD', child: Text('SSD')),
          DropdownMenuItem(value: 'HDD', child: Text('HDD')),
        ],
        onChanged: (value) => setState(() => _storageType = value ?? 'SSD'),
      ),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _display, decoration: const InputDecoration(labelText: 'Display')),
      const SizedBox(height: AppSpacing.sm),
      TextField(controller: _colorOptions, decoration: const InputDecoration(labelText: 'Color options')),
      const SizedBox(height: AppSpacing.sm),
      TextField(
        controller: _specNotes,
        decoration: const InputDecoration(labelText: 'Additional specs'),
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
          onPressed: _fetching ? null : _runAutoFetch,
          child: Text(_fetching ? 'Fetching…' : 'Auto fetch'),
        ),
      ),
    ];
  }

  Widget _specsStepActions(BuildContext context) {
    final canAdvance = _modelName.text.trim().isNotEmpty && _cpu.text.trim().isNotEmpty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!canAdvance)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              'Enter model name and CPU to continue.',
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
    return [
      Text(
        '${_modelNumber.text.trim()} — ${_modelName.text.trim()}',
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: AppSpacing.sm),
      Text('${_validUnits().length} unit(s) · New model'),
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
  });

  final TextEditingController serial;
  int locationId;

  void dispose() {
    serial.dispose();
  }
}
