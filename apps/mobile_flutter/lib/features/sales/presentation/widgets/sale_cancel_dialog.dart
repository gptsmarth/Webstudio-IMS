import 'package:flutter/material.dart';

import '../../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../domain/sales_models.dart';

Future<String?> showSaleCancelDialog(
  BuildContext context,
  SaleListItem sale,
) {
  return showModalBottomSheet<String?>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheetForm(
      child: _SaleCancelForm(sale: sale),
    ),
  );
}

Future<String?> showSaleCancelDialogForDetail(
  BuildContext context,
  SaleDetail detail,
) {
  return showModalBottomSheet<String?>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheetForm(
      child: _SaleCancelForm(
        invoiceNumber: detail.invoiceNumber,
        serialNumber: detail.serialNumber,
        modelNumber: detail.modelNumber,
      ),
    ),
  );
}

class _SaleCancelForm extends StatefulWidget {
  const _SaleCancelForm({
    this.sale,
    this.invoiceNumber,
    this.serialNumber,
    this.modelNumber,
  }) : assert(
          sale != null ||
              (invoiceNumber != null && serialNumber != null && modelNumber != null),
        );

  final SaleListItem? sale;
  final String? invoiceNumber;
  final String? serialNumber;
  final String? modelNumber;

  @override
  State<_SaleCancelForm> createState() => _SaleCancelFormState();
}

class _SaleCancelFormState extends State<_SaleCancelForm> {
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  String get _invoiceNumber => widget.sale?.invoiceNumber ?? widget.invoiceNumber!;
  String get _serialNumber => widget.sale?.serialNumber ?? widget.serialNumber!;
  String get _modelNumber => widget.sale?.modelNumber ?? widget.modelNumber!;

  void _submit() {
    Navigator.of(context).pop(_reasonController.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Delete invoice', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        Text(
          'This will delete invoice $_invoiceNumber and return serial $_serialNumber '
          '($_modelNumber) to available stock. This action cannot be undone.',
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _reasonController,
          maxLines: 3,
          maxLength: 2000,
          decoration: const InputDecoration(
            labelText: 'Reason (optional)',
            hintText: 'Customer return, wrong invoice, etc.',
          ),
        ),
        const SizedBox(height: 16),
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
                style: FilledButton.styleFrom(
                  backgroundColor: colorScheme.error,
                  foregroundColor: colorScheme.onError,
                ),
                onPressed: _submit,
                child: const Text('Delete invoice'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
