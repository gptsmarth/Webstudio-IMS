import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'version_check_controller.dart';
import 'version_models.dart';

/// Blocks interaction when a mandatory update is required.
class MandatoryUpdateGate extends ConsumerWidget {
  const MandatoryUpdateGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checkState = ref.watch(versionCheckControllerProvider);
    final outcome = checkState.outcome;
    if (!checkState.mandatoryBlocked || outcome?.kind != VersionUpdateKind.mandatoryUpdate) {
      return child;
    }

    final remote = outcome!.remote!;
    return Material(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              Icon(Icons.system_update_alt, size: 56, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 16),
              Text(
                'Update required',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              const Text(
                'This version of WEBSTUDIO IMS is no longer supported.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text('Installed: ${outcome.installedVersion}', textAlign: TextAlign.center),
              Text('Minimum supported: ${remote.minSupportedVersion}', textAlign: TextAlign.center),
              Text('Latest available: ${remote.latestVersion}', textAlign: TextAlign.center),
              const Spacer(),
              FilledButton(
                onPressed: () => launchApkDownloadUrl(remote.apkDownloadUrl),
                child: const Text('Update Now'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
