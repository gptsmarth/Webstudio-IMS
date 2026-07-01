import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/placeholders.dart';
import '../data/audit_repository.dart';
import '../domain/audit_models.dart';

class AuditCenterScreen extends ConsumerStatefulWidget {
  const AuditCenterScreen({super.key});

  @override
  ConsumerState<AuditCenterScreen> createState() => _AuditCenterScreenState();
}

class _AuditCenterScreenState extends ConsumerState<AuditCenterScreen> {
  final _searchController = TextEditingController();
  bool _loading = false;
  String? _error;
  List<AuditLogEntry> _items = const [];
  int _page = 1;
  int _totalPages = 1;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load({int page = 1}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await ref.read(auditRepositoryProvider).list(
            search: _searchController.text,
            page: page,
          );
      if (!mounted) return;
      setState(() {
        _items = result.items;
        _page = result.page;
        _totalPages = result.totalPages;
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

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: const InputDecoration(
                      hintText: 'Search audit logs…',
                      prefixIcon: Icon(Icons.search, size: 20),
                      isDense: true,
                    ),
                    onSubmitted: (_) => _load(),
                  ),
                ),
                IconButton(icon: const Icon(Icons.refresh), onPressed: () => _load(page: _page)),
              ],
            ),
          ),
          if (_loading) const LinearProgressIndicator(minHeight: 2),
          if (_error != null) ErrorBanner(message: _error!, onRetry: () => _load(page: _page)),
          Expanded(
            child: _items.isEmpty && !_loading
                ? const EmptyStateView(
                    icon: Icons.history,
                    title: 'No audit entries',
                    message: 'Audit events will appear here as users perform operations.',
                  )
                : RefreshIndicator(
                    onRefresh: () => _load(page: _page),
                    child: ListView.separated(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final entry = _items[index];
                        return ListTile(
                          leading: const Icon(Icons.history, size: 20),
                          title: Text(entry.description),
                          subtitle: Text(
                            '${entry.module} · ${entry.operation} · ${entry.createdAt.split('T').first}',
                          ),
                          trailing: entry.actorDisplayName == null
                              ? null
                              : Text(entry.actorDisplayName!, style: Theme.of(context).textTheme.labelSmall),
                        );
                      },
                    ),
                  ),
          ),
          if (_totalPages > 1)
            SafeArea(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton(
                    onPressed: _page > 1 ? () => _load(page: _page - 1) : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Text('Page $_page of $_totalPages'),
                  IconButton(
                    onPressed: _page < _totalPages ? () => _load(page: _page + 1) : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
            ),
        ],
    );
  }
}
