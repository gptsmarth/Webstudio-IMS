import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../inventory/domain/inventory_models.dart';
import '../../data/report_filter_reference.dart';
import '../../domain/report_date_presets.dart';
import '../../domain/report_models.dart';

Future<ReportQueryParams?> showReportFiltersSheet(
  BuildContext context, {
  required ReportType reportType,
  required ReportQueryParams initial,
  required ReportFilterReference reference,
}) {
  return showModalBottomSheet<ReportQueryParams>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => _ReportFiltersSheet(
      reportType: reportType,
      initial: initial,
      reference: reference,
    ),
  );
}

class _ReportFiltersSheet extends StatefulWidget {
  const _ReportFiltersSheet({
    required this.reportType,
    required this.initial,
    required this.reference,
  });

  final ReportType reportType;
  final ReportQueryParams initial;
  final ReportFilterReference reference;

  @override
  State<_ReportFiltersSheet> createState() => _ReportFiltersSheetState();
}

class _ReportFiltersSheetState extends State<_ReportFiltersSheet> {
  late String _datePreset;
  late String _dateFrom;
  late String _dateTo;
  late int? _brandId;
  late int? _locationId;
  late String _locationType;
  late String? _productModelId;
  late String _inventoryStatus;
  late String _saleSource;
  late String _auditAction;
  late String _auditSource;
  late String _actorRole;
  late String _syncStatus;
  late String _tallyOutcome;
  late String _notificationType;

  late final TextEditingController _searchController;
  late final TextEditingController _serialController;
  late final TextEditingController _colorController;
  late final TextEditingController _invoiceController;
  late final TextEditingController _customerController;
  late final TextEditingController _userIdController;
  late final TextEditingController _paymentModeController;
  late final TextEditingController _companyController;

  @override
  void initState() {
    super.initState();
    final initial = widget.initial;
    _datePreset = initial.datePreset;
    _dateFrom = initial.dateFrom;
    _dateTo = initial.dateTo;
    _brandId = initial.brandId;
    _locationId = initial.locationId;
    _locationType = initial.locationType;
    _productModelId = initial.productModelId;
    _inventoryStatus = initial.inventoryStatus;
    _saleSource = initial.saleSource;
    _auditAction = initial.auditAction;
    _auditSource = initial.auditSource;
    _actorRole = initial.actorRole;
    _syncStatus = initial.syncStatus;
    _tallyOutcome = initial.tallyOutcome;
    _notificationType = initial.notificationType;
    _searchController = TextEditingController(text: initial.search);
    _serialController = TextEditingController(text: initial.serialNumber);
    _colorController = TextEditingController(text: initial.color);
    _invoiceController = TextEditingController(text: initial.invoiceNumber);
    _customerController = TextEditingController(text: initial.customerName);
    _userIdController = TextEditingController(text: initial.userId?.toString() ?? '');
    _paymentModeController = TextEditingController(text: initial.paymentMode);
    _companyController = TextEditingController(text: initial.company);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _serialController.dispose();
    _colorController.dispose();
    _invoiceController.dispose();
    _customerController.dispose();
    _userIdController.dispose();
    _paymentModeController.dispose();
    _companyController.dispose();
    super.dispose();
  }

  void _reset() {
    setState(() {
      _datePreset = '';
      _dateFrom = '';
      _dateTo = '';
      _brandId = null;
      _locationId = null;
      _locationType = '';
      _productModelId = null;
      _inventoryStatus = '';
      _saleSource = '';
      _auditAction = '';
      _auditSource = '';
      _actorRole = '';
      _syncStatus = '';
      _tallyOutcome = '';
      _notificationType = '';
      _searchController.clear();
      _serialController.clear();
      _colorController.clear();
      _invoiceController.clear();
      _customerController.clear();
      _userIdController.clear();
      _paymentModeController.clear();
      _companyController.clear();
    });
  }

  ReportQueryParams _buildResult() {
    final userId = int.tryParse(_userIdController.text.trim());
    return widget.initial.copyWith(
      page: 1,
      search: _searchController.text,
      datePreset: _datePreset,
      dateFrom: _dateFrom,
      dateTo: _dateTo,
      brandId: _brandId,
      clearBrandId: _brandId == null,
      locationId: _locationId,
      clearLocationId: _locationId == null,
      locationType: _locationType,
      productModelId: _productModelId,
      clearProductModelId: _productModelId == null,
      serialNumber: _serialController.text,
      inventoryStatus: _inventoryStatus,
      color: _colorController.text,
      userId: userId,
      clearUserId: userId == null,
      invoiceNumber: _invoiceController.text,
      customerName: _customerController.text,
      paymentMode: _paymentModeController.text,
      saleSource: _saleSource,
      auditAction: _auditAction,
      auditSource: _auditSource,
      actorRole: _actorRole,
      notificationType: _notificationType,
      syncStatus: _syncStatus,
      tallyOutcome: _tallyOutcome,
      company: _companyController.text,
    );
  }

  List<ProductModel> get _modelsForBrand {
    final brandId = _brandId;
    if (brandId == null) return widget.reference.productModels;
    return widget.reference.productModels.where((model) => model.brandId == brandId).toList();
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.88,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Configure filters', style: Theme.of(context).textTheme.titleMedium),
                        Text(
                          '${widget.reportType.label} report — combinable filters',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  ..._typeFilters(),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      labelText: 'Search',
                      hintText: switch (widget.reportType) {
                        ReportType.inventory => 'Serial, brand, model, location…',
                        ReportType.sales => 'Invoice, customer, serial…',
                        ReportType.audit => 'Description, actor, serial…',
                        ReportType.tally => 'Title, description, invoice…',
                      },
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Row(
                children: [
                  TextButton(onPressed: _reset, child: const Text('Reset')),
                  const Spacer(),
                  TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, _buildResult()),
                    child: const Text('Apply filters'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _typeFilters() {
    return switch (widget.reportType) {
      ReportType.inventory => _inventoryFilters(),
      ReportType.sales => _salesFilters(),
      ReportType.audit => _auditFilters(),
      ReportType.tally => _tallyFilters(),
    };
  }

  List<Widget> _referenceFields({bool includeStoreType = true}) {
    return [
      if (includeStoreType)
        DropdownButtonFormField<String>(
          // ignore: deprecated_member_use
          value: _locationType.isEmpty ? null : _locationType,
          decoration: const InputDecoration(labelText: 'Store type'),
          items: const [
            DropdownMenuItem(value: null, child: Text('All stores')),
            DropdownMenuItem(value: 'warehouse', child: Text('Warehouse')),
            DropdownMenuItem(value: 'retail_floor', child: Text('Retail floor')),
            DropdownMenuItem(value: 'other', child: Text('Other')),
          ],
          onChanged: (value) => setState(() => _locationType = value ?? ''),
        ),
      const SizedBox(height: 8),
      DropdownButtonFormField<int?>(
        // ignore: deprecated_member_use
        value: _locationId,
        decoration: const InputDecoration(labelText: 'Location'),
        items: [
          const DropdownMenuItem(value: null, child: Text('All locations')),
          ...widget.reference.locations.map(
            (Location location) => DropdownMenuItem(value: location.id, child: Text(location.name)),
          ),
        ],
        onChanged: (value) => setState(() => _locationId = value),
      ),
      const SizedBox(height: 8),
      DropdownButtonFormField<int?>(
        // ignore: deprecated_member_use
        value: _brandId,
        decoration: const InputDecoration(labelText: 'Brand'),
        items: [
          const DropdownMenuItem(value: null, child: Text('All brands')),
          ...widget.reference.brands.where((Brand brand) => brand.isActive).map(
                (Brand brand) => DropdownMenuItem(value: brand.id, child: Text(brand.name)),
              ),
        ],
        onChanged: (value) => setState(() {
          _brandId = value;
          _productModelId = null;
        }),
      ),
      const SizedBox(height: 8),
      DropdownButtonFormField<String?>(
        // ignore: deprecated_member_use
        value: _productModelId,
        decoration: const InputDecoration(labelText: 'Product model'),
        items: [
          const DropdownMenuItem(value: null, child: Text('All models')),
          ..._modelsForBrand.map(
            (ProductModel model) => DropdownMenuItem(
              value: model.id,
              child: Text('${model.modelNumber} — ${model.modelName}'),
            ),
          ),
        ],
        onChanged: (value) => setState(() => _productModelId = value),
      ),
      const SizedBox(height: 8),
    ];
  }

  List<Widget> _datePresetFields({required bool showPresets, required String dateLabel}) {
    return [
      if (showPresets) ...[
        DropdownButtonFormField<String>(
          // ignore: deprecated_member_use
          value: _datePreset.isEmpty ? null : _datePreset,
          decoration: InputDecoration(labelText: dateLabel),
          items: [
            const DropdownMenuItem(value: null, child: Text('All dates')),
            ...ReportDatePresets.labels.entries
                .where((MapEntry<String, String> entry) => entry.key.isNotEmpty)
                .map((MapEntry<String, String> entry) => DropdownMenuItem(value: entry.key, child: Text(entry.value))),
          ],
          onChanged: (value) => setState(() => _datePreset = value ?? ''),
        ),
        const SizedBox(height: 8),
      ],
      if (!showPresets || _datePreset == ReportDatePresets.custom || _datePreset.isEmpty) ...[
        _dateTile(
          label: '$dateLabel from',
          value: _dateFrom,
          onPicked: (value) => setState(() {
            _dateFrom = value;
            _datePreset = ReportDatePresets.custom;
          }),
        ),
        _dateTile(
          label: '$dateLabel to',
          value: _dateTo,
          onPicked: (value) => setState(() {
            _dateTo = value;
            _datePreset = ReportDatePresets.custom;
          }),
        ),
        const SizedBox(height: 8),
      ],
    ];
  }

  Widget _dateTile({
    required String label,
    required String value,
    required ValueChanged<String> onPicked,
  }) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(label),
      subtitle: Text(value.isEmpty ? 'Any' : value),
      trailing: const Icon(Icons.calendar_today, size: 18),
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: DateTime.tryParse(value) ?? DateTime.now(),
          firstDate: DateTime(2020),
          lastDate: DateTime.now().add(const Duration(days: 365)),
        );
        if (picked == null) return;
        onPicked(picked.toIso8601String().split('T').first);
      },
    );
  }

  List<Widget> _inventoryFilters() {
    return [
      ..._referenceFields(),
      TextField(controller: _serialController, decoration: const InputDecoration(labelText: 'Serial number')),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _inventoryStatus.isEmpty ? null : _inventoryStatus,
        decoration: const InputDecoration(labelText: 'Status'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All statuses')),
          DropdownMenuItem(value: 'available', child: Text('Available')),
          DropdownMenuItem(value: 'sold', child: Text('Sold')),
          DropdownMenuItem(value: 'archived', child: Text('Archived')),
        ],
        onChanged: (value) => setState(() => _inventoryStatus = value ?? ''),
      ),
      const SizedBox(height: 8),
      ..._datePresetFields(showPresets: true, dateLabel: 'Created date'),
      TextField(controller: _colorController, decoration: const InputDecoration(labelText: 'Color')),
      const SizedBox(height: 8),
    ];
  }

  List<Widget> _salesFilters() {
    return [
      ..._datePresetFields(showPresets: true, dateLabel: 'Sale date'),
      ..._referenceFields(),
      TextField(controller: _serialController, decoration: const InputDecoration(labelText: 'Serial number')),
      const SizedBox(height: 8),
      TextField(controller: _invoiceController, decoration: const InputDecoration(labelText: 'Invoice number')),
      const SizedBox(height: 8),
      TextField(controller: _customerController, decoration: const InputDecoration(labelText: 'Customer')),
      const SizedBox(height: 8),
      TextField(
        controller: _userIdController,
        decoration: const InputDecoration(labelText: 'Salesperson (user ID)'),
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      ),
      const SizedBox(height: 8),
      TextField(controller: _paymentModeController, decoration: const InputDecoration(labelText: 'Payment mode')),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _saleSource.isEmpty ? null : _saleSource,
        decoration: const InputDecoration(labelText: 'Sale source'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All sources')),
          DropdownMenuItem(value: 'manual', child: Text('Manual')),
          DropdownMenuItem(value: 'tally', child: Text('Tally')),
        ],
        onChanged: (value) => setState(() => _saleSource = value ?? ''),
      ),
      const SizedBox(height: 8),
    ];
  }

  List<Widget> _auditFilters() {
    return [
      TextField(
        controller: _userIdController,
        decoration: const InputDecoration(labelText: 'User ID'),
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      ),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _actorRole.isEmpty ? null : _actorRole,
        decoration: const InputDecoration(labelText: 'Role'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All roles')),
          DropdownMenuItem(value: 'main_admin', child: Text('Main admin')),
          DropdownMenuItem(value: 'admin', child: Text('Admin')),
          DropdownMenuItem(value: 'salesperson', child: Text('Salesperson')),
        ],
        onChanged: (value) => setState(() => _actorRole = value ?? ''),
      ),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _auditAction.isEmpty ? null : _auditAction,
        decoration: const InputDecoration(labelText: 'Operation'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All operations')),
          DropdownMenuItem(value: 'CREATE', child: Text('Create')),
          DropdownMenuItem(value: 'UPDATE', child: Text('Update')),
          DropdownMenuItem(value: 'ARCHIVE', child: Text('Archive')),
          DropdownMenuItem(value: 'RESTORE', child: Text('Restore')),
          DropdownMenuItem(value: 'STATUS_CHANGE', child: Text('Status change')),
          DropdownMenuItem(value: 'LOCATION_CHANGE', child: Text('Location change')),
          DropdownMenuItem(value: 'SYSTEM_ACTION', child: Text('System action')),
        ],
        onChanged: (value) => setState(() => _auditAction = value ?? ''),
      ),
      const SizedBox(height: 8),
      ..._datePresetFields(showPresets: false, dateLabel: 'Date'),
      TextField(controller: _serialController, decoration: const InputDecoration(labelText: 'Serial number')),
      const SizedBox(height: 8),
      ..._referenceFields(includeStoreType: false),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _auditSource.isEmpty ? null : _auditSource,
        decoration: const InputDecoration(labelText: 'Action source'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All sources')),
          DropdownMenuItem(value: 'MANUAL', child: Text('Manual')),
          DropdownMenuItem(value: 'TALLY_SYNC', child: Text('Tally sync')),
          DropdownMenuItem(value: 'BACKGROUND_JOB', child: Text('Background job')),
          DropdownMenuItem(value: 'SYSTEM', child: Text('System')),
        ],
        onChanged: (value) => setState(() => _auditSource = value ?? ''),
      ),
      const SizedBox(height: 8),
    ];
  }

  List<Widget> _tallyFilters() {
    return [
      TextField(controller: _companyController, decoration: const InputDecoration(labelText: 'Company')),
      const SizedBox(height: 8),
      ..._datePresetFields(showPresets: true, dateLabel: 'Date'),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _syncStatus.isEmpty ? null : _syncStatus,
        decoration: const InputDecoration(labelText: 'Sync status'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All statuses')),
          DropdownMenuItem(value: 'unread', child: Text('Unread')),
          DropdownMenuItem(value: 'read', child: Text('Read')),
          DropdownMenuItem(value: 'resolved', child: Text('Resolved')),
        ],
        onChanged: (value) => setState(() => _syncStatus = value ?? ''),
      ),
      const SizedBox(height: 8),
      TextField(controller: _invoiceController, decoration: const InputDecoration(labelText: 'Invoice number')),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _tallyOutcome.isEmpty ? null : _tallyOutcome,
        decoration: const InputDecoration(labelText: 'Outcome'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All outcomes')),
          DropdownMenuItem(value: 'processed', child: Text('Processed')),
          DropdownMenuItem(value: 'skipped', child: Text('Skipped')),
          DropdownMenuItem(value: 'duplicate', child: Text('Duplicate')),
          DropdownMenuItem(value: 'missing_serial', child: Text('Missing serial')),
          DropdownMenuItem(value: 'missing_model', child: Text('Missing model')),
          DropdownMenuItem(value: 'model_mismatch', child: Text('Model mismatch')),
        ],
        onChanged: (value) => setState(() {
          _tallyOutcome = value ?? '';
          _notificationType = '';
        }),
      ),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        // ignore: deprecated_member_use
        value: _notificationType.isEmpty ? null : _notificationType,
        decoration: const InputDecoration(labelText: 'Notification type'),
        items: const [
          DropdownMenuItem(value: null, child: Text('All types')),
          DropdownMenuItem(value: 'tally_sync_completed', child: Text('Tally sync completed')),
          DropdownMenuItem(value: 'sync_failure', child: Text('Sync failure')),
          DropdownMenuItem(value: 'duplicate_sale', child: Text('Duplicate sale')),
          DropdownMenuItem(value: 'serial_number_missing', child: Text('Serial number missing')),
          DropdownMenuItem(value: 'product_model_missing', child: Text('Product model missing')),
          DropdownMenuItem(value: 'product_model_mismatch', child: Text('Product model mismatch')),
        ],
        onChanged: _tallyOutcome.isNotEmpty
            ? null
            : (value) => setState(() => _notificationType = value ?? ''),
      ),
      const SizedBox(height: 8),
    ];
  }
}
