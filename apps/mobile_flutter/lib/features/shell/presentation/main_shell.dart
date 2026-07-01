import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart' hide ShellRouteContext;

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/shell_route_titles.dart';
import '../../../core/theme/app_breakpoints.dart';
import '../../../core/theme/app_spacing.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../auth/presentation/session_manager.dart';
import '../../../shared/widgets/offline_banner.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../../shared/widgets/shell_back_button.dart';
import '../../../shared/widgets/workspace_layout.dart';
import '../../search/presentation/global_search_screen.dart';
import 'shell_chrome_controller.dart';
import 'shell_navigation_controller.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int? _lastSyncedBranch;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncNavigationBranch());
  }

  void _syncNavigationBranch() {
    if (!mounted) return;
    final permissions = effectivePermissions(ref.read(authControllerProvider).user);
    final navItems = mobileNavItemsFor(permissions);
    if (navItems.isEmpty) return;

    final targetBranch = navItems.first.branchIndex;
    final current = widget.navigationShell.currentIndex;
    if (!isBranchAllowedForPermissions(current, permissions)) {
      if (_lastSyncedBranch == targetBranch) return;
      _lastSyncedBranch = targetBranch;
      widget.navigationShell.goBranch(targetBranch);
    } else {
      _lastSyncedBranch = current;
    }
  }

  void _selectBranch(int branchIndex) {
    final fromBranch = widget.navigationShell.currentIndex;
    if (fromBranch == branchIndex) return;

    ref.read(shellNavigationProvider.notifier).recordBranchChange(
          fromBranch: fromBranch,
          toBranch: branchIndex,
        );

    if (branchIndex != MobileShellBranch.stock && branchIndex != MobileShellBranch.inventory) {
      ref.read(shellChromeProvider.notifier).clear();
    }

    widget.navigationShell.goBranch(branchIndex);
  }

  bool _canInventoryBack(ShellChromeState chrome, int branch) {
    return chrome.hasBack &&
        (branch == MobileShellBranch.stock || branch == MobileShellBranch.inventory);
  }

  bool _canNestedPop(BuildContext context, ShellRouteContext routeContext) {
    return routeContext.canPopRoute && context.canPop();
  }

  bool _canTabBack(ShellNavigationState navigation, int currentBranch) {
    final previous = navigation.previousBranchIndex;
    return previous != null && previous != currentBranch;
  }

  void _handleBack({
    required BuildContext context,
    required ShellChromeState chrome,
    required ShellRouteContext routeContext,
    required ShellNavigationState navigation,
    required int branch,
  }) {
    if (_canInventoryBack(chrome, branch) && chrome.onBack != null) {
      chrome.onBack!();
      return;
    }
    if (_canNestedPop(context, routeContext)) {
      context.pop();
      return;
    }
    final previousBranch = navigation.previousBranchIndex;
    if (previousBranch != null && previousBranch != branch) {
      _selectBranch(previousBranch);
      ref.read(shellNavigationProvider.notifier).clearPreviousBranch();
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authControllerProvider, (previous, next) {
      final authChanged = previous?.status != next.status ||
          previous?.user?.id != next.user?.id ||
          previous?.user?.role != next.user?.role;
      if (authChanged) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _syncNavigationBranch());
      }
    });

    final user = ref.watch(authControllerProvider).user;
    final permissions = effectivePermissions(user);
    final navItems = mobileNavItemsFor(permissions);
    final stockOnly = isStockOnlyUser(permissions);
    final useRail = AppBreakpoints.isTablet(context);

    final selectedNavIndex = navItems.indexWhere((item) => item.branchIndex == widget.navigationShell.currentIndex);
    final safeSelectedIndex = selectedNavIndex >= 0 ? selectedNavIndex : 0;

    final location = GoRouterState.of(context).matchedLocation;
    final routeContext = shellRouteContext(location);
    final chrome = ref.watch(shellChromeProvider);
    final navigation = ref.watch(shellNavigationProvider);
    final branch = widget.navigationShell.currentIndex;

    final inventoryBack = _canInventoryBack(chrome, branch);
    final nestedPop = _canNestedPop(context, routeContext);
    final tabBack = _canTabBack(navigation, branch);
    final canStepBack = inventoryBack || nestedPop || tabBack;

    final title = inventoryBack && chrome.title != null ? chrome.title! : routeContext.title;

    void handleBack() => _handleBack(
          context: context,
          chrome: chrome,
          routeContext: routeContext,
          navigation: navigation,
          branch: branch,
        );

    return SessionManager(
      child: PopScope(
        canPop: !canStepBack,
        onPopInvokedWithResult: (didPop, _) {
          if (!didPop && canStepBack) handleBack();
        },
        child: Scaffold(
          appBar: AppBar(
            automaticallyImplyLeading: false,
            leadingWidth: canStepBack ? 104 : null,
            leading: canStepBack ? ShellBackButton(onPressed: handleBack) : null,
            title: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: Text(
                title,
                key: ValueKey(title),
              ),
            ),
            actions: [
              if (!stockOnly && !chrome.hideGlobalSearch)
                IconButton(
                  icon: const Icon(Icons.search),
                  tooltip: 'Global search',
                  onPressed: () {
                    Navigator.of(context).push<void>(
                      MaterialPageRoute<void>(builder: (_) => const GlobalSearchScreen()),
                    );
                  },
                ),
              if (user != null)
                Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.md),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: BoxConstraints(maxWidth: useRail ? 160 : 120),
                      child: Text(
                        user.displayLabel,
                        style: Theme.of(context).textTheme.labelMedium,
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          body: OfflineBanner(
            child: navItems.isEmpty
                ? const EmptyStateView(
                    icon: Icons.lock_outline,
                    title: 'No modules available',
                    message: 'Your account does not have permission to access any workspace modules. Contact your administrator.',
                  )
                : useRail
                    ? Row(
                        children: [
                          NavigationRail(
                            selectedIndex: safeSelectedIndex,
                            onDestinationSelected: (index) => _selectBranch(navItems[index].branchIndex),
                            labelType: NavigationRailLabelType.all,
                            destinations: [
                              for (final item in navItems)
                                NavigationRailDestination(
                                  icon: Icon(item.icon),
                                  selectedIcon: Icon(item.selectedIcon),
                                  label: Text(item.label),
                                ),
                            ],
                          ),
                          const VerticalDivider(width: 1),
                          Expanded(
                            child: FadeIn(
                              key: ValueKey(widget.navigationShell.currentIndex),
                              child: widget.navigationShell,
                            ),
                          ),
                        ],
                      )
                    : FadeIn(
                        key: ValueKey(widget.navigationShell.currentIndex),
                        child: widget.navigationShell,
                      ),
          ),
          bottomNavigationBar: useRail || navItems.isEmpty
              ? null
              : NavigationBar(
                  selectedIndex: safeSelectedIndex,
                  onDestinationSelected: (index) => _selectBranch(navItems[index].branchIndex),
                  destinations: [
                    for (final item in navItems)
                      NavigationDestination(
                        icon: Icon(item.icon),
                        selectedIcon: Icon(item.selectedIcon),
                        label: item.label,
                      ),
                  ],
                ),
        ),
      ),
    );
  }
}
