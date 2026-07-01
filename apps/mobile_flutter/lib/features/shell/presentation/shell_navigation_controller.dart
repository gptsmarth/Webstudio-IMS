import 'package:flutter_riverpod/flutter_riverpod.dart';

class ShellNavigationState {
  const ShellNavigationState({this.previousBranchIndex});

  final int? previousBranchIndex;
}

class ShellNavigationController extends StateNotifier<ShellNavigationState> {
  ShellNavigationController() : super(const ShellNavigationState());

  void recordBranchChange({required int fromBranch, required int toBranch}) {
    if (fromBranch == toBranch) return;
    state = ShellNavigationState(previousBranchIndex: fromBranch);
  }

  void clearPreviousBranch() {
    if (state.previousBranchIndex == null) return;
    state = const ShellNavigationState();
  }
}

final shellNavigationProvider =
    StateNotifierProvider<ShellNavigationController, ShellNavigationState>((ref) {
  return ShellNavigationController();
});
