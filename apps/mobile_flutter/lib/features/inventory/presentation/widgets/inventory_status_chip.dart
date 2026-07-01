import 'package:flutter/material.dart';

import '../../domain/inventory_models.dart';

class InventoryStatusChip extends StatelessWidget {
  const InventoryStatusChip({super.key, required this.status, this.isArchived = false});

  final InventoryStatus status;
  final bool isArchived;

  @override
  Widget build(BuildContext context) {
    final (label, color) = _style(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600),
      ),
    );
  }

  (String, Color) _style(BuildContext context) {
    if (isArchived) return ('Archived', Theme.of(context).colorScheme.outline);
    return switch (status) {
      InventoryStatus.received => ('Received', Theme.of(context).colorScheme.primary),
      InventoryStatus.available => ('Available', Colors.green.shade700),
      InventoryStatus.reserved => ('Reserved', Colors.orange.shade800),
      InventoryStatus.sold => ('Sold', Theme.of(context).colorScheme.error),
    };
  }
}
