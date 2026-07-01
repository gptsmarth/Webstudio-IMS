import 'package:flutter/material.dart';

import '../../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../domain/inventory_models.dart';

const paymentModes = ['Cash', 'Card', 'UPI', 'Bank Transfer', 'Finance'];

Future<MarkSoldRequest?> showMarkSoldDialog(
  BuildContext context,
  String serialNumber, {
  double? defaultSaleAmount,
}) {
  return showModalBottomSheet<MarkSoldRequest>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheetForm(
      child: _MarkSoldForm(
        serialNumber: serialNumber,
        defaultSaleAmount: defaultSaleAmount,
      ),
    ),
  );
}

class _MarkSoldForm extends StatefulWidget {
  const _MarkSoldForm({
    required this.serialNumber,
    this.defaultSaleAmount,
  });

  final String serialNumber;
  final double? defaultSaleAmount;

  @override
  State<_MarkSoldForm> createState() => _MarkSoldFormState();
}

class _MarkSoldFormState extends State<_MarkSoldForm> {
  final _invoiceController = TextEditingController();
  final _customerController = TextEditingController();
  final _amountController = TextEditingController();
  final _remarksController = TextEditingController();
  String _paymentMode = paymentModes.first;
  DateTime _saleDate = DateTime.now();
  String? _error;

  @override
  void initState() {
    super.initState();
    final amount = widget.defaultSaleAmount;
    if (amount != null && amount > 0) {
      _amountController.text = amount.toStringAsFixed(0);
    }
  }

  @override
  void dispose() {
    _invoiceController.dispose();
    _customerController.dispose();
    _amountController.dispose();
    _remarksController.dispose();
    super.dispose();
  }

  void _submit() {
    if (_invoiceController.text.trim().isEmpty || _customerController.text.trim().isEmpty) {
      setState(() => _error = 'Invoice number and customer name are required.');
      return;
    }
    Navigator.of(context).pop(
      MarkSoldRequest(
        invoiceNumber: _invoiceController.text.trim(),
        customerName: _customerController.text.trim(),
        paymentMode: _paymentMode,
        saleDate: _saleDate.toIso8601String().split('T').first,
        saleAmount: _amountController.text.trim().isEmpty ? null : double.tryParse(_amountController.text.trim()),
        remarks: _remarksController.text.trim().isEmpty ? null : _remarksController.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Mark as sold', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        Text(
          widget.serialNumber,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
        ),
        const SizedBox(height: 16),
        TextField(controller: _invoiceController, decoration: const InputDecoration(labelText: 'Invoice number')),
        const SizedBox(height: 12),
        TextField(controller: _customerController, decoration: const InputDecoration(labelText: 'Customer name')),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          // ignore: deprecated_member_use
          value: _paymentMode,
          items: paymentModes.map((mode) => DropdownMenuItem(value: mode, child: Text(mode))).toList(),
          onChanged: (value) => setState(() => _paymentMode = value ?? paymentModes.first),
          decoration: const InputDecoration(labelText: 'Payment mode'),
        ),
        const SizedBox(height: 12),
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Sale date'),
          subtitle: Text(_saleDate.toIso8601String().split('T').first),
          trailing: const Icon(Icons.calendar_today, size: 18),
          onTap: () async {
            final picked = await showDatePicker(
              context: context,
              initialDate: _saleDate,
              firstDate: DateTime(2020),
              lastDate: DateTime.now().add(const Duration(days: 1)),
            );
            if (picked != null) setState(() => _saleDate = picked);
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _amountController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Sale amount (optional)', prefixText: '₹ '),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _remarksController,
          decoration: const InputDecoration(labelText: 'Remarks (optional)'),
          maxLines: 2,
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ],
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton(
                onPressed: _submit,
                child: const Text('Confirm sale'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

Future<int?> showTransferLocationDialog(
  BuildContext context, {
  required List<Location> locations,
  required int currentLocationId,
}) {
  return showDialog<int>(
    context: context,
    builder: (context) => _TransferDialog(locations: locations, currentLocationId: currentLocationId),
  );
}

class _TransferDialog extends StatefulWidget {
  const _TransferDialog({required this.locations, required this.currentLocationId});

  final List<Location> locations;
  final int currentLocationId;

  @override
  State<_TransferDialog> createState() => _TransferDialogState();
}

class _TransferDialogState extends State<_TransferDialog> {
  late int _locationId;

  @override
  void initState() {
    super.initState();
    final options = widget.locations.where((l) => l.id != widget.currentLocationId).toList();
    _locationId = options.isNotEmpty ? options.first.id : widget.currentLocationId;
  }

  @override
  Widget build(BuildContext context) {
    final options = widget.locations.where((l) => l.id != widget.currentLocationId).toList();
    return AlertDialog(
      title: const Text('Transfer location'),
      content: DropdownButtonFormField<int>(
        // ignore: deprecated_member_use
        value: _locationId,
        items: options.map((l) => DropdownMenuItem(value: l.id, child: Text(l.name))).toList(),
        onChanged: (value) => setState(() => _locationId = value ?? _locationId),
        decoration: const InputDecoration(labelText: 'Destination'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(onPressed: () => Navigator.of(context).pop(_locationId), child: const Text('Transfer')),
      ],
    );
  }
}

Future<double?> showEditSellingPriceDialog(BuildContext context, double? currentPrice) {
  return showDialog<double>(
    context: context,
    builder: (context) => _EditSellingPriceDialog(currentPrice: currentPrice),
  );
}

class _EditSellingPriceDialog extends StatefulWidget {
  const _EditSellingPriceDialog({required this.currentPrice});

  final double? currentPrice;

  @override
  State<_EditSellingPriceDialog> createState() => _EditSellingPriceDialogState();
}

class _EditSellingPriceDialogState extends State<_EditSellingPriceDialog> {
  late final TextEditingController _priceController;

  @override
  void initState() {
    super.initState();
    _priceController = TextEditingController(
      text: widget.currentPrice != null && widget.currentPrice! > 0 ? widget.currentPrice!.toStringAsFixed(0) : '',
    );
  }

  @override
  void dispose() {
    _priceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit selling price'),
      content: TextField(
        controller: _priceController,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: const InputDecoration(labelText: 'Selling price (₹)', prefixText: '₹ '),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(
          onPressed: () {
            final raw = _priceController.text.trim();
            final price = raw.isEmpty ? null : double.tryParse(raw);
            Navigator.of(context).pop(price);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

Future<Map<String, dynamic>?> showEditInventoryDialog(BuildContext context, InventoryItem item) {
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => _EditInventoryDialog(item: item),
  );
}

class _EditInventoryDialog extends StatefulWidget {
  const _EditInventoryDialog({required this.item});

  final InventoryItem item;

  @override
  State<_EditInventoryDialog> createState() => _EditInventoryDialogState();
}

class _EditInventoryDialogState extends State<_EditInventoryDialog> {
  late final TextEditingController _colorController;
  late final TextEditingController _serialController;

  @override
  void initState() {
    super.initState();
    _colorController = TextEditingController(text: widget.item.color);
    _serialController = TextEditingController(text: widget.item.serialNumber);
  }

  @override
  void dispose() {
    _colorController.dispose();
    _serialController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit inventory unit'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _serialController,
            decoration: const InputDecoration(labelText: 'Serial number'),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _colorController,
            decoration: const InputDecoration(labelText: 'Color'),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(
          onPressed: () => Navigator.of(context).pop({
            'serial_number': _serialController.text.trim(),
            'color': _colorController.text.trim(),
          }),
          child: const Text('Save'),
        ),
      ],
    );
  }
}
