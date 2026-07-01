import 'package:flutter/material.dart';

/// Adaptive master-detail layout for tablet widths (≥900px).
class AdaptiveMasterDetail extends StatelessWidget {
  const AdaptiveMasterDetail({
    super.key,
    required this.master,
    required this.detail,
    this.hasSelection = false,
    this.tabletBreakpoint = 900,
  });

  final Widget master;
  final Widget? detail;
  final bool hasSelection;
  final double tabletBreakpoint;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final useSplit = width >= tabletBreakpoint;

    if (!useSplit) {
      return master;
    }

    return Row(
      children: [
        SizedBox(width: width * 0.38, child: master),
        const VerticalDivider(width: 1),
        Expanded(
          child: hasSelection && detail != null
              ? detail!
              : Center(
                  child: Text(
                    'Select an item',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: Theme.of(context).colorScheme.outline,
                        ),
                  ),
                ),
        ),
      ],
    );
  }
}
