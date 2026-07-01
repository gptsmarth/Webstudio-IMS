import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/rbac/mobile_navigation.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../inventory/presentation/inventory_controller.dart';
import '../data/global_search_orchestrator.dart';
import '../domain/search_models.dart';

class GlobalSearchScreen extends ConsumerStatefulWidget {
  const GlobalSearchScreen({super.key});

  @override
  ConsumerState<GlobalSearchScreen> createState() => _GlobalSearchScreenState();
}

class _GlobalSearchScreenState extends ConsumerState<GlobalSearchScreen> {
  final _controller = TextEditingController();
  String _query = '';
  bool _loading = false;
  String? _error;
  GlobalSearchResult? _result;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    final term = query.trim();
    if (term.length < 2) {
      setState(() {
        _query = term;
        _result = null;
        _error = null;
      });
      return;
    }
    setState(() {
      _query = term;
      _loading = true;
      _error = null;
    });
    try {
      final permissions = effectivePermissions(ref.read(authControllerProvider).user);
      final result = await ref.read(globalSearchOrchestratorProvider).searchAll(term, permissions: permissions);
      if (!mounted) return;
      setState(() {
        _result = result;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _openHit(GlobalSearchHit hit) async {
    switch (hit.type) {
      case 'inventory':
        await ref.read(inventoryWorkspaceProvider.notifier).openItemBySerial(hit.title);
        if (mounted) {
          final permissions = effectivePermissions(ref.read(authControllerProvider).user);
          context.go(
            permissions.contains('inventory:create') ? AppRoutes.inventory : AppRoutes.stock,
          );
        }
      case 'sale':
        if (mounted) context.go(AppRoutes.sales);
      case 'audit':
        if (mounted) context.push(AppRoutes.audit);
      case 'notification':
        if (mounted) context.push(AppRoutes.notifications);
      case 'user':
        if (mounted) context.push(AppRoutes.users);
      case 'brand':
        if (mounted) context.go(AppRoutes.catalogue);
      case 'location':
        if (mounted) context.go(AppRoutes.catalogue);
      case 'product_model':
        if (mounted) {
          final permissions = effectivePermissions(ref.read(authControllerProvider).user);
          context.go(
            permissions.contains('inventory:create') ? AppRoutes.inventory : AppRoutes.stock,
          );
        }
      default:
        break;
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'Search inventory, sales, users, audit…',
            border: InputBorder.none,
          ),
          onChanged: (value) {
            Future<void>.delayed(const Duration(milliseconds: 350), () {
              if (_controller.text == value) _search(value);
            });
          },
          onSubmitted: _search,
        ),
      ),
      body: Column(
        children: [
          if (_loading) const LinearProgressIndicator(minHeight: 2),
          if (_error != null) ErrorBanner(message: _error!, onRetry: () => _search(_query)),
          Expanded(
            child: _result == null
                ? EmptyStateView(
                    icon: Icons.search,
                    title: _query.isEmpty ? 'Global search' : 'Keep typing…',
                    message: _query.isEmpty
                        ? 'Search across inventory, sales, catalogue, users, audit, and notifications.'
                        : 'Enter at least 2 characters.',
                  )
                : _result!.hits.isEmpty
                    ? EmptyStateView(
                        icon: Icons.search_off,
                        title: 'No results',
                        message: 'Nothing matched "$_query".',
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        itemCount: _result!.hits.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final hit = _result!.hits[index];
                          return ListTile(
                            leading: Icon(_iconForType(hit.type)),
                            title: Text(hit.title),
                            subtitle: Text(hit.subtitle),
                            trailing: Chip(label: Text(hit.type.replaceAll('_', ' '))),
                            onTap: () => _openHit(hit),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  IconData _iconForType(String type) => switch (type) {
        'inventory' => Icons.inventory_2_outlined,
        'brand' => Icons.branding_watermark_outlined,
        'location' => Icons.place_outlined,
        'product_model' => Icons.laptop_mac_outlined,
        'sale' => Icons.point_of_sale_outlined,
        'audit' => Icons.history,
        'notification' => Icons.notifications_outlined,
        'user' => Icons.person_outline,
        _ => Icons.search,
      };
}
