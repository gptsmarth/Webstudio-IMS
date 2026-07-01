import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../core/rbac/role_permissions.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/settings_repository.dart';
import '../data/settings_write_repository.dart';

Future<void> showSettingsWritePanel(BuildContext context, WidgetRef ref) async {
  final permissions = effectivePermissions(ref.read(authControllerProvider).user);
  if (!canWriteSettings(permissions)) {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('You do not have permission to edit settings.')));
    return;
  }
  final workspace = await ref.read(settingsWorkspaceProvider.future);
  final companyController = TextEditingController(text: workspace.companyName);
  final tallyHostController = TextEditingController(text: workspace.tally.tallyHost);
  final tallyPortController = TextEditingController(text: '${workspace.tally.tallyPort}');
  var aiEnabled = workspace.integrations.aiEnrichmentEnabled;

  if (!context.mounted) return;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => Padding(
        padding: EdgeInsets.only(left: 24, right: 24, top: 24, bottom: MediaQuery.viewInsetsOf(context).bottom + 24),
        child: ListView(
          shrinkWrap: true,
          children: [
            Text('Edit settings', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            Text('Company', style: Theme.of(context).textTheme.titleSmall),
            TextField(controller: companyController, decoration: const InputDecoration(labelText: 'Company name')),
            const SizedBox(height: AppSpacing.lg),
            Text('Tally', style: Theme.of(context).textTheme.titleSmall),
            TextField(controller: tallyHostController, decoration: const InputDecoration(labelText: 'Host')),
            TextField(controller: tallyPortController, decoration: const InputDecoration(labelText: 'Port'), keyboardType: TextInputType.number),
            SwitchListTile(
              title: const Text('Tally enabled'),
              value: workspace.tally.enabled,
              onChanged: null,
            ),
            const SizedBox(height: AppSpacing.lg),
            Text('AI enrichment', style: Theme.of(context).textTheme.titleSmall),
            SwitchListTile(
              title: const Text('AI enrichment enabled'),
              value: aiEnabled,
              onChanged: (v) => setState(() => aiEnabled = v),
            ),
            const SizedBox(height: AppSpacing.lg),
            FilledButton(
              onPressed: () async {
                final write = ref.read(settingsWriteRepositoryProvider);
                await write.patchGeneral({'company_name': companyController.text.trim()});
                await write.patchTally({
                  'tally_host': tallyHostController.text.trim(),
                  'tally_port': int.tryParse(tallyPortController.text.trim()) ?? workspace.tally.tallyPort,
                });
                await write.patchIntegrations({'ai_enrichment_enabled': aiEnabled});
                ref.invalidate(settingsWorkspaceProvider);
                if (context.mounted) Navigator.pop(context);
              },
              child: const Text('Save'),
            ),
            if (canManageIntegrationKeys(permissions)) ...[
              const Divider(height: 32),
              Text('Integration API keys', style: Theme.of(context).textTheme.titleSmall),
              FutureBuilder(
                future: ref.read(settingsWriteRepositoryProvider).listIntegrationKeys(),
                builder: (context, snapshot) {
                  final keys = snapshot.data ?? const [];
                  if (keys.isEmpty) return const Text('No keys configured');
                  return Column(
                    children: keys.take(5).map((k) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(k['name']?.toString() ?? 'Key'),
                          subtitle: Text(k['prefix']?.toString() ?? '—'),
                        )).toList(),
                  );
                },
              ),
            ],
          ],
        ),
      ),
    ),
  );
}
