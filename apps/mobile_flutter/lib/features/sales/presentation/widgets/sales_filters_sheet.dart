import 'package:flutter/material.dart';

import '../../../inventory/domain/inventory_models.dart';
import '../../domain/sales_models.dart';
import '../sales_controller.dart';

Future<SalesListFilters?> showSalesFiltersSheet(
  BuildContext context, {
  required SalesListFilters initial,
  required List<Brand> brands,
  required List<Location> locations,
  required List<SalespersonOption> salespeople,
}) {
  return showModalBottomSheet<SalesListFilters>(
    context: context,
    isScrollControlled: true,
    builder: (context) => _SalesFiltersSheet(
      initial: initial,
      brands: brands,
      locations: locations,
      salespeople: salespeople,
    ),
  );
}
class _SalesFiltersSheet extends StatefulWidget {
  const _SalesFiltersSheet({
    required this.initial,
    required this.brands,
    required this.locations,
    required this.salespeople,
  });

  final SalesListFilters initial;
  final List<Brand> brands;
  final List<Location> locations;
  final List<SalespersonOption> salespeople;

  @override
  State<_SalesFiltersSheet> createState() => _SalesFiltersSheetState();
}

class _SalesFiltersSheetState extends State<_SalesFiltersSheet> {
  late int? _brandId;
  late int? _locationId;
  late int? _userId;
  late TextEditingController _invoiceController;
  late TextEditingController _customerController;
  late String _paymentMode;
  late String _saleSource;
  late DateTime? _dateFrom;
  late DateTime? _dateTo;

  @override
  void initState() {
    super.initState();
    _brandId = widget.initial.brandId;
    _locationId = widget.initial.locationId;
    _userId = widget.initial.userId;
    _invoiceController = TextEditingController(text: widget.initial.invoiceNumber);
    _customerController = TextEditingController(text: widget.initial.customerName);
    _paymentMode = widget.initial.paymentMode;
    _saleSource = widget.initial.saleSource;
    _dateFrom = widget.initial.dateFrom.isNotEmpty ? DateTime.tryParse(widget.initial.dateFrom) : null;
    _dateTo = widget.initial.dateTo.isNotEmpty ? DateTime.tryParse(widget.initial.dateTo) : null;
  }

  @override
  void dispose() {
    _invoiceController.dispose();
    _customerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Sales filters', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            DropdownButtonFormField<int?>(
              // ignore: deprecated_member_use
              value: _brandId,
              decoration: const InputDecoration(labelText: 'Brand'),
              items: [
                const DropdownMenuItem(value: null, child: Text('All brands')),
                ...widget.brands.where((b) => b.isActive).map(
                      (b) => DropdownMenuItem(value: b.id, child: Text(b.name)),
                    ),
              ],
              onChanged: (v) => setState(() => _brandId = v),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<int?>(
              // ignore: deprecated_member_use
              value: _locationId,
              decoration: const InputDecoration(labelText: 'Store'),
              items: [
                const DropdownMenuItem(value: null, child: Text('All stores')),
                ...widget.locations.map((l) => DropdownMenuItem(value: l.id, child: Text(l.name))),
              ],
              onChanged: (v) => setState(() => _locationId = v),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<int?>(
              // ignore: deprecated_member_use
              value: _userId,
              decoration: const InputDecoration(labelText: 'Salesperson'),
              items: [
                const DropdownMenuItem(value: null, child: Text('All')),
                ...widget.salespeople.map(
                  (p) => DropdownMenuItem(value: p.id, child: Text(p.displayName)),
                ),
              ],
              onChanged: (v) => setState(() => _userId = v),
            ),
            const SizedBox(height: 8),
            TextField(controller: _invoiceController, decoration: const InputDecoration(labelText: 'Invoice')),
            const SizedBox(height: 8),
            TextField(controller: _customerController, decoration: const InputDecoration(labelText: 'Customer')),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              // ignore: deprecated_member_use
              value: _paymentMode.isEmpty ? null : _paymentMode,
              decoration: const InputDecoration(labelText: 'Payment mode'),
              items: [
                const DropdownMenuItem(value: null, child: Text('Any')),
                ...paymentModes.map((m) => DropdownMenuItem(value: m, child: Text(m))),
              ],
              onChanged: (v) => setState(() => _paymentMode = v ?? ''),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              // ignore: deprecated_member_use
              value: _saleSource.isEmpty ? null : _saleSource,
              decoration: const InputDecoration(labelText: 'Sale source'),
              items: const [
                DropdownMenuItem(value: null, child: Text('Any')),
                DropdownMenuItem(value: 'manual', child: Text('Manual')),
                DropdownMenuItem(value: 'tally', child: Text('Tally')),
              ],
              onChanged: (v) => setState(() => _saleSource = v ?? ''),
            ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Date from'),
              subtitle: Text(_dateFrom?.toIso8601String().split('T').first ?? 'Any'),
              trailing: const Icon(Icons.calendar_today, size: 18),
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: _dateFrom ?? DateTime.now(),
                  firstDate: DateTime(2020),
                  lastDate: DateTime.now(),
                );
                if (picked != null) setState(() => _dateFrom = picked);
              },
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Date to'),
              subtitle: Text(_dateTo?.toIso8601String().split('T').first ?? 'Any'),
              trailing: const Icon(Icons.calendar_today, size: 18),
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: _dateTo ?? DateTime.now(),
                  firstDate: DateTime(2020),
                  lastDate: DateTime.now(),
                );
                if (picked != null) setState(() => _dateTo = picked);
              },
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                const Spacer(),
                TextButton(
                  onPressed: () {
                    setState(() {
                      _brandId = null;
                      _locationId = null;
                      _userId = null;
                      _invoiceController.clear();
                      _customerController.clear();
                      _paymentMode = '';
                      _saleSource = '';
                      _dateFrom = null;
                      _dateTo = null;
                    });
                  },
                  child: const Text('Reset'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pop(
                      context,
                      SalesListFilters(
                        brandId: _brandId,
                        locationId: _locationId,
                        userId: _userId,
                        invoiceNumber: _invoiceController.text,
                        customerName: _customerController.text,
                        paymentMode: _paymentMode,
                        saleSource: _saleSource,
                        dateFrom: _dateFrom?.toIso8601String().split('T').first ?? '',
                        dateTo: _dateTo?.toIso8601String().split('T').first ?? '',
                      ),
                    );
                  },
                  child: const Text('Apply'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
