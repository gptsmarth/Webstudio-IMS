import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_config_provider.dart';
import 'client_update_installer.dart';
import 'version_models.dart';
import 'version_repository.dart';

final versionCheckControllerProvider =
    StateNotifierProvider<VersionCheckController, VersionCheckState>((ref) {
  return VersionCheckController(ref);
});

class VersionCheckState {
  const VersionCheckState({
    this.outcome,
    this.checking = false,
    this.mandatoryBlocked = false,
  });

  final VersionCheckOutcome? outcome;
  final bool checking;
  final bool mandatoryBlocked;

  VersionCheckState copyWith({
    VersionCheckOutcome? outcome,
    bool? checking,
    bool? mandatoryBlocked,
  }) {
    return VersionCheckState(
      outcome: outcome ?? this.outcome,
      checking: checking ?? this.checking,
      mandatoryBlocked: mandatoryBlocked ?? this.mandatoryBlocked,
    );
  }
}

class VersionCheckController extends StateNotifier<VersionCheckState> {
  VersionCheckController(this._ref) : super(const VersionCheckState());

  final Ref _ref;

  VersionRepository get _repository => _ref.read(versionRepositoryProvider);

  Future<VersionCheckOutcome?> check({
    required VersionCheckTrigger trigger,
    bool force = false,
    bool showDialogs = true,
    BuildContext? context,
  }) async {
    state = state.copyWith(checking: true);
    final outcome = await _repository.checkForUpdates(force: force || trigger == VersionCheckTrigger.manual);
    state = state.copyWith(checking: false, outcome: outcome);

    if (outcome.errorMessage != null) {
      if (showDialogs && context != null && context.mounted && trigger == VersionCheckTrigger.manual) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(outcome.errorMessage!)));
      }
      return outcome;
    }

    final remote = outcome.remote;
    if (remote == null) return outcome;

    switch (outcome.kind) {
      case VersionUpdateKind.mandatoryUpdate:
        state = state.copyWith(mandatoryBlocked: true);
        if (showDialogs && context != null && context.mounted) {
          await showMandatoryUpdateDialog(context, outcome: outcome, ref: _ref);
        }
        break;
      case VersionUpdateKind.optionalUpdate:
        if (_repository.shouldSuppressOptionalPrompt() && trigger != VersionCheckTrigger.manual) {
          return outcome;
        }
        if (showDialogs && context != null && context.mounted) {
          await showOptionalUpdateDialog(context, outcome: outcome, repository: _repository, ref: _ref);
        }
        break;
      case VersionUpdateKind.upToDate:
        if (showDialogs && context != null && context.mounted && trigger == VersionCheckTrigger.manual) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('You are running the latest available version.')),
          );
        }
        break;
    }
    return outcome;
  }
}

enum VersionCheckTrigger { startup, login, periodic, manual }

Future<void> showOptionalUpdateDialog(
  BuildContext context, {
  required VersionCheckOutcome outcome,
  required VersionRepository repository,
  required Ref ref,
}) {
  final remote = outcome.remote!;
  return showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Update available'),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_updateIntro(remote)),
            const SizedBox(height: 12),
            Text('Current version: ${outcome.installedVersion}'),
            Text('Latest version: ${remote.latestVersion}'),
            if (remote.releaseDate != null && remote.releaseDate!.isNotEmpty)
              Text('Release date: ${remote.releaseDate}'),
            if (remote.releaseNotes != null && remote.releaseNotes!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Release notes', style: Theme.of(context).textTheme.titleSmall),
              Text(remote.releaseNotes!),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () async {
            await repository.remindLater();
            if (dialogContext.mounted) Navigator.pop(dialogContext);
          },
          child: const Text('Remind Me Later'),
        ),
        FilledButton(
          onPressed: () async {
            await _performClientUpdate(ref, remote, dialogContext);
          },
          child: Text(remote.isAppStoreNotification ? 'View in App Store' : 'Update Now'),
        ),
      ],
    ),
  );
}

Future<void> showMandatoryUpdateDialog(
  BuildContext context, {
  required VersionCheckOutcome outcome,
  required Ref ref,
}) {
  final remote = outcome.remote!;
  return showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (dialogContext) => PopScope(
      canPop: false,
      child: AlertDialog(
        title: const Text('Update required'),
        content: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_updateIntro(remote)),
            const SizedBox(height: 12),
            Text('Installed: ${outcome.installedVersion}'),
            Text('Minimum supported: ${remote.minSupportedVersion}'),
            Text('Latest available: ${remote.latestVersion}'),
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => _performClientUpdate(ref, remote, dialogContext),
            child: Text(remote.isAppStoreNotification ? 'Open App Store' : 'Update Now'),
          ),
        ],
      ),
    ),
  );
}

String _updateIntro(MobileVersionInfo remote) {
  if (remote.isAppStoreNotification) {
    return 'A newer version of WEBSTUDIO IMS is available on the App Store. '
        'Install updates through the App Store — direct IPA installation is not supported.';
  }
  return 'A new version of WEBSTUDIO IMS is available from your WEBSTUDIO Server.';
}

Future<void> _performClientUpdate(Ref ref, MobileVersionInfo remote, BuildContext dialogContext) async {
  try {
    if (remote.isAppStoreNotification || (!kIsWeb && Platform.isIOS)) {
      await launchAppStoreUrl(remote.appStoreUrl);
    } else if (!kIsWeb && Platform.isAndroid) {
      final installer = ClientUpdateInstaller(config: ref.read(appConfigProvider));
      await installer.installAndroidUpdate(remote);
    } else {
      await launchApkDownloadUrl(remote.apkDownloadUrl);
    }
    if (dialogContext.mounted) Navigator.pop(dialogContext);
  } catch (error) {
    if (dialogContext.mounted) {
      ScaffoldMessenger.of(dialogContext).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
  }
}

Future<void> launchAppStoreUrl(String? url) async {
  final target = url?.trim();
  if (target == null || target.isEmpty) {
    throw StateError('App Store URL is not configured on the server.');
  }
  final uri = Uri.tryParse(target);
  if (uri == null) {
    throw StateError('Invalid App Store URL.');
  }
  await launchUrl(uri, mode: LaunchMode.externalApplication);
}

Future<void> launchApkDownloadUrl(String? url) async {
  final target = url?.trim();
  if (target == null || target.isEmpty) return;
  final uri = Uri.tryParse(target);
  if (uri == null) return;
  await launchUrl(uri, mode: LaunchMode.externalApplication);
}
