import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../core/config/app_config_provider.dart';
import '../../../core/version/version_check_controller.dart';
import '../../../core/version/version_repository.dart';

class VersionAboutSection extends ConsumerWidget {
  const VersionAboutSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final installed = ref.watch(appConfigProvider).clientVersion;
    final repository = ref.watch(versionRepositoryProvider);
    final checkState = ref.watch(versionCheckControllerProvider);
    final latestRemote = checkState.outcome?.remote ?? repository.cachedRemote;
    final lastCheck = repository.lastCheckAt;
    final formatter = DateFormat.yMMMd().add_jm();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Text('About / Version', style: Theme.of(context).textTheme.titleSmall),
        ),
        ListTile(
          leading: const Icon(Icons.info_outline),
          title: const Text('Current app version'),
          subtitle: Text(installed),
        ),
        ListTile(
          leading: const Icon(Icons.system_update_alt_outlined),
          title: const Text('Latest available version'),
          subtitle: Text(latestRemote?.latestVersion ?? '—'),
        ),
        ListTile(
          leading: const Icon(Icons.dns_outlined),
          title: const Text('Backend version'),
          subtitle: Text(latestRemote?.backendVersion ?? '—'),
        ),
        ListTile(
          leading: const Icon(Icons.layers_outlined),
          title: const Text('Release channel'),
          subtitle: Text(_channelLabel(latestRemote?.releaseChannel)),
        ),
        ListTile(
          leading: const Icon(Icons.schedule_outlined),
          title: const Text('Last update check'),
          subtitle: Text(lastCheck == null ? 'Never' : formatter.format(lastCheck.toLocal())),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: FilledButton.icon(
            onPressed: checkState.checking
                ? null
                : () => ref.read(versionCheckControllerProvider.notifier).check(
                      trigger: VersionCheckTrigger.manual,
                      force: true,
                      context: context,
                    ),
            icon: checkState.checking
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
            label: const Text('Check for Updates'),
          ),
        ),
      ],
    );
  }

  String _channelLabel(String? channel) {
    if (channel == null || channel.isEmpty) return '—';
    if (channel.toLowerCase() == 'beta') return 'Beta';
    return 'Stable';
  }
}
