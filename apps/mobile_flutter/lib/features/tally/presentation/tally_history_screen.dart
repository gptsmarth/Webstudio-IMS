import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/device/file_transfer_service.dart';
import '../../../core/theme/app_spacing.dart';
import '../data/tally_repository.dart';
import '../domain/tally_models.dart';

class TallyHistoryScreen extends ConsumerStatefulWidget {
  const TallyHistoryScreen({super.key});

  @override
  ConsumerState<TallyHistoryScreen> createState() => _TallyHistoryScreenState();
}

class _TallyHistoryScreenState extends ConsumerState<TallyHistoryScreen> {
  String _status = '';
  String _search = '';
  DateTime? _dateFrom;
  DateTime? _dateTo;

  TallySyncHistoryFilters get _filters => TallySyncHistoryFilters(
        status: _status.isEmpty ? null : _status,
        search: _search.trim().isEmpty ? null : _search.trim(),
        dateFrom: _dateFrom != null ? _formatDate(_dateFrom!) : null,
        dateTo: _dateTo != null ? _formatDate(_dateTo!) : null,
      );

  static String _formatDate(DateTime date) =>
      '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate({required bool isFrom}) async {
    final initial = isFrom ? _dateFrom : _dateTo;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked == null) return;
    setState(() {
      if (isFrom) {
        _dateFrom = picked;
      } else {
        _dateTo = picked;
      }
    });
  }

  Future<void> _export() async {
    final file = await ref.read(tallyRepositoryProvider).exportSyncHistory(_filters);
    await ref.read(fileTransferServiceProvider).shareFile(
          filename: file.filename,
          bytes: file.bytes,
          mimeType: 'text/csv',
        );
  }

  @override
  Widget build(BuildContext context) {
    final history = ref.watch(tallySyncHistoryProvider(_filters));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tally Sync History'),
        actions: [
          IconButton(
            tooltip: 'Export CSV',
            onPressed: () async {
              try {
                await _export();
              } catch (error) {
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
              }
            },
            icon: const Icon(Icons.download_outlined),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              children: [
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Search',
                    hintText: 'Status or error message',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onChanged: (value) => setState(() => _search = value),
                  onSubmitted: (_) => ref.invalidate(tallySyncHistoryProvider(_filters)),
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String?>(
                        initialValue: _status.isEmpty ? null : _status,
                        decoration: const InputDecoration(labelText: 'Status'),
                        items: const [
                          DropdownMenuItem(value: null, child: Text('All statuses')),
                          DropdownMenuItem(value: 'success', child: Text('Success')),
                          DropdownMenuItem(value: 'partial', child: Text('Partial')),
                          DropdownMenuItem(value: 'failed', child: Text('Failed')),
                          DropdownMenuItem(value: 'offline', child: Text('Skipped (offline)')),
                        ],
                        onChanged: (value) => setState(() => _status = value ?? ''),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => _pickDate(isFrom: true),
                        child: Text(_dateFrom == null ? 'From date' : 'From ${_formatDate(_dateFrom!)}'),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => _pickDate(isFrom: false),
                        child: Text(_dateTo == null ? 'To date' : 'To ${_formatDate(_dateTo!)}'),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Apply filters',
                      onPressed: () => ref.invalidate(tallySyncHistoryProvider(_filters)),
                      icon: const Icon(Icons.filter_alt_outlined),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: history.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Center(child: Text(error.toString())),
              data: (entries) {
                if (entries.isEmpty) {
                  return const Center(child: Text('No synchronization runs match your filters.'));
                }
                return ListView.separated(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                  itemCount: entries.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) => _HistoryTile(entry: entries[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.entry});

  final TallySyncHistoryEntry entry;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text('${entry.syncDate} · ${entry.startTime}–${entry.endTime ?? '—'}'),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Checked ${entry.invoicesChecked} · Imported ${entry.invoicesImported} · '
            'Skipped ${entry.invoicesSkipped} · Errors ${entry.errorsCount}',
          ),
          Text('Duration ${entry.durationLabel} · ${entry.statusLabel}'),
          if (entry.errorSummary != null && entry.errorSummary!.isNotEmpty)
            Text(entry.errorSummary!, maxLines: 2, overflow: TextOverflow.ellipsis),
        ],
      ),
      isThreeLine: true,
    );
  }
}
