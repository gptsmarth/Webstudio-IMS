import 'package:flutter/material.dart';

/// Modal bottom sheet with a scrollable list body — avoids yellow overflow stripes
/// when content is taller than the space above the bottom navigation bar.
Future<T?> showScrollableBottomSheet<T>({
  required BuildContext context,
  String? title,
  required List<Widget> children,
  double maxHeightFactor = 0.72,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheet(
      title: title,
      maxHeightFactor: maxHeightFactor,
      children: children,
    ),
  );
}

class ScrollableBottomSheet extends StatelessWidget {
  const ScrollableBottomSheet({
    super.key,
    this.title,
    required this.children,
    this.maxHeightFactor = 0.72,
    this.padding = const EdgeInsets.symmetric(vertical: 4),
  });

  final String? title;
  final List<Widget> children;
  final double maxHeightFactor;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final maxHeight = MediaQuery.sizeOf(context).height * maxHeightFactor;
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: maxHeight),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (title != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Text(title!, style: Theme.of(context).textTheme.titleMedium),
            ),
          Flexible(
            child: ListView(
              padding: padding,
              shrinkWrap: true,
              children: children,
            ),
          ),
        ],
      ),
    );
  }
}

/// Scrollable form/content wrapper for modal bottom sheets (keyboard-safe).
class ScrollableBottomSheetForm extends StatelessWidget {
  const ScrollableBottomSheetForm({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(24),
    this.maxHeightFactor = 0.88,
  });

  final Widget child;
  final EdgeInsets padding;
  final double maxHeightFactor;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.viewInsetsOf(context).bottom;
    final maxHeight = MediaQuery.sizeOf(context).height * maxHeightFactor;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: maxHeight),
        child: SingleChildScrollView(
          padding: padding,
          child: child,
        ),
      ),
    );
  }
}
