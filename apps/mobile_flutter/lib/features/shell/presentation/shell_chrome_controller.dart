import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Lets workspace screens override the shell AppBar title, back action, and trailing controls.
class ShellChromeState {
  const ShellChromeState({
    this.title,
    this.onBack,
    this.hideGlobalSearch = false,
  });

  final String? title;
  final VoidCallback? onBack;
  final bool hideGlobalSearch;

  bool get hasBack => onBack != null;
}

class ShellChromeController extends StateNotifier<ShellChromeState> {
  ShellChromeController() : super(const ShellChromeState());

  void set({
    String? title,
    VoidCallback? onBack,
    bool hideGlobalSearch = false,
  }) {
    state = ShellChromeState(
      title: title,
      onBack: onBack,
      hideGlobalSearch: hideGlobalSearch,
    );
  }

  void clear() => state = const ShellChromeState();
}

final shellChromeProvider =
    StateNotifierProvider<ShellChromeController, ShellChromeState>((ref) {
  return ShellChromeController();
});
