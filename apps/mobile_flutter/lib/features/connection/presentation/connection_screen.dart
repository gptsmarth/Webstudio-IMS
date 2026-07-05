import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/config/app_config_provider.dart';
import '../../../core/routing/app_routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/startup_shell.dart';
import '../presentation/connection_controller.dart';
import '../domain/server_models.dart';

class ConnectionScreen extends ConsumerStatefulWidget {
  const ConnectionScreen({super.key, this.onConnected});

  final VoidCallback? onConnected;

  @override
  ConsumerState<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends ConsumerState<ConnectionScreen> {
  final _urlController = TextEditingController();
  final _urlFocus = FocusNode();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final connection = ref.read(connectionControllerProvider);
      _urlController.text = connection.manualUrl.isNotEmpty
          ? connection.manualUrl
          : AppConfig.suggestedManualServerUrl();
      ref.read(connectionControllerProvider.notifier).startAutoDiscovery();
    });
  }

  @override
  void dispose() {
    ref.read(connectionControllerProvider.notifier).cancelDiscovery();
    _urlController.dispose();
    _urlFocus.dispose();
    super.dispose();
  }

  Future<void> _handleConnected() async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    if (!mounted) return;
    if (widget.onConnected != null) {
      widget.onConnected!();
    } else {
      context.go(AppRoutes.bootstrap);
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(connectionControllerProvider, (previous, next) {
      if (previous?.phase != ConnectionPhase.found && next.phase == ConnectionPhase.found) {
        _handleConnected();
      }
      if (next.phase == ConnectionPhase.manual && _urlController.text != next.manualUrl) {
        _urlController.text = next.manualUrl;
        _urlFocus.requestFocus();
      }
    });

    final connection = ref.watch(connectionControllerProvider);
    final currentUrl = ref.watch(appConfigProvider).apiBaseUrl;
    final footerStatus = switch (connection.phase) {
      ConnectionPhase.found => 'Connected',
      ConnectionPhase.searching => 'Scanning network',
      _ => 'Manual configuration',
    };

    return StartupShellLayout(
      footerRight: connection.phase == ConnectionPhase.searching
          ? 'CONNECTING'
          : connection.phase == ConnectionPhase.found
              ? 'CONNECTED'
              : 'SETUP',
      child: ListView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        children: [
          Text('Connect to Server', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'WEBSTUDIO IMS needs the API server before sign-in can begin.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (currentUrl.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            Chip(
              avatar: const Icon(Icons.dns_outlined, size: 16),
              label: Text(currentUrl, style: const TextStyle(fontSize: 12)),
            ),
          ],
          const SizedBox(height: AppSpacing.xl),
          if (connection.phase != ConnectionPhase.found)
            _ManualForm(
              controller: _urlController,
              focusNode: _urlFocus,
              busy: connection.phase == ConnectionPhase.testing,
              compact: connection.phase == ConnectionPhase.searching,
              errorMessage: connection.errorMessage,
              diagnosticStages: connection.diagnosticStages,
              onSubmit: () =>
                  ref.read(connectionControllerProvider.notifier).connectToUrl(_urlController.text.trim()),
              onRetryDiscovery: () => ref.read(connectionControllerProvider.notifier).startAutoDiscovery(),
              onSkipDiscovery: connection.phase == ConnectionPhase.searching
                  ? () => ref.read(connectionControllerProvider.notifier).skipToManualEntry()
                  : null,
            ),
          _StatusCard(connection: connection),
          if (connection.discoveredServers.isNotEmpty &&
              connection.phase != ConnectionPhase.found) ...[
            const SizedBox(height: AppSpacing.lg),
            Text('Discovered on your network', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: AppSpacing.sm),
            ...connection.discoveredServers.map(
              (server) => Card(
                child: ListTile(
                  leading: const Icon(Icons.wifi_find),
                  title: Text(server.companyName),
                  subtitle: Text(
                    '${server.serverName} · v${server.backendVersion} · ${server.status} · '
                    'Last seen ${_formatLastSeen(server.lastSeen)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  trailing: ElevatedButton(
                    onPressed: connection.phase == ConnectionPhase.testing
                        ? null
                        : () => ref.read(connectionControllerProvider.notifier).connectToUrl(server.url),
                    child: const Text('Connect'),
                  ),
                ),
              ),
            ),
          ],
          if (connection.savedServers.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.xl),
            Text('Saved servers', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: AppSpacing.sm),
            ...connection.savedServers.map(
              (server) => Card(
                child: ListTile(
                  leading: const Icon(Icons.history),
                  title: Text(server.displayLabel),
                  subtitle: Text(
                    '${server.url}${server.backendVersion != null ? ' · v${server.backendVersion}' : ''}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    onPressed: connection.phase == ConnectionPhase.testing
                        ? null
                        : () => ref.read(connectionControllerProvider.notifier).removeSaved(server.url),
                  ),
                  onTap: connection.phase == ConnectionPhase.testing
                      ? null
                      : () {
                          _urlController.text = server.url;
                          ref.read(connectionControllerProvider.notifier).connectToUrl(server.url);
                        },
                ),
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.xl),
          Row(
            children: [
              Icon(Icons.wifi, size: 14, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: AppSpacing.sm),
              Text(footerStatus, style: Theme.of(context).textTheme.labelMedium),
            ],
          ),
        ],
      ),
    );
  }
}

String _formatLastSeen(DateTime dateTime) {
  return '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.connection});

  final ServerConnectionState connection;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: switch (connection.phase) {
          ConnectionPhase.searching => Row(
              children: [
                const SizedBox(
                  width: 36,
                  height: 36,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                ),
                const SizedBox(width: AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Connecting to server', style: Theme.of(context).textTheme.titleSmall),
                      const SizedBox(height: 4),
                      Text(
                        '${ConnectionController.discoveryMessages[connection.messageIndex]}…',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ConnectionPhase.found => Row(
              children: [
                Icon(Icons.check_circle_outline, color: Theme.of(context).colorScheme.primary, size: 36),
                const SizedBox(width: AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Server found', style: Theme.of(context).textTheme.titleSmall),
                      Text(
                        connection.lastResult?.companyName ?? 'Establishing secure connection…',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ConnectionPhase.manual || ConnectionPhase.testing => Row(
              children: [
                Icon(Icons.dns_outlined, color: Theme.of(context).colorScheme.secondary, size: 32),
                const SizedBox(width: AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Server not found', style: Theme.of(context).textTheme.titleSmall),
                      Text(
                        'Enter your WEBSTUDIO Server address manually or retry automatic discovery.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
        },
      ),
    );
  }
}

class _ManualForm extends StatelessWidget {
  const _ManualForm({
    required this.controller,
    required this.focusNode,
    required this.busy,
    required this.onSubmit,
    required this.onRetryDiscovery,
    this.compact = false,
    this.onSkipDiscovery,
    this.errorMessage,
    this.diagnosticStages,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final bool busy;
  final bool compact;
  final String? errorMessage;
  final List<ConnectionStageResult>? diagnosticStages;
  final VoidCallback onSubmit;
  final VoidCallback onRetryDiscovery;
  final VoidCallback? onSkipDiscovery;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: AppSpacing.lg),
        if (compact)
          Text(
            'Searching your Wi‑Fi automatically. You can connect manually anytime using the address below.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        if (compact) const SizedBox(height: AppSpacing.sm),
        if (errorMessage != null) ...[
          Material(
            color: Theme.of(context).colorScheme.errorContainer,
            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Row(
                children: [
                  Icon(Icons.error_outline, color: Theme.of(context).colorScheme.error, size: 18),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(child: Text(errorMessage!, style: Theme.of(context).textTheme.bodySmall)),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        if (diagnosticStages != null && diagnosticStages!.isNotEmpty) ...[
          ...diagnosticStages!.map(
            (stage) => ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                stage.success ? Icons.check_circle_outline : Icons.cancel_outlined,
                size: 18,
                color: stage.success
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.error,
              ),
              title: Text(stage.label, style: Theme.of(context).textTheme.bodySmall),
              subtitle: stage.success ? null : Text(stage.message, style: Theme.of(context).textTheme.labelSmall),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: const InputDecoration(
            labelText: 'Server address',
            hintText: 'http://192.168.29.100:8000',
            helperText: 'Use your shop server IP (not 10.0.2.2 — emulator only). Hostname or .local also works.',
          ),
          keyboardType: TextInputType.url,
          enabled: !busy,
          onSubmitted: (_) => onSubmit(),
        ),
        const SizedBox(height: AppSpacing.lg),
        ValueListenableBuilder<TextEditingValue>(
          valueListenable: controller,
          builder: (context, value, _) {
            final canSubmit = !busy && value.text.trim().isNotEmpty;
            return ElevatedButton(
              onPressed: canSubmit ? onSubmit : null,
              child: busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Connect to server'),
                        SizedBox(width: AppSpacing.sm),
                        Icon(Icons.arrow_forward, size: 16),
                      ],
                    ),
            );
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        if (onSkipDiscovery != null)
          TextButton(
            onPressed: busy ? null : onSkipDiscovery,
            child: const Text('Stop searching — use manual address only'),
          ),
        TextButton.icon(
          onPressed: busy ? null : onRetryDiscovery,
          icon: const Icon(Icons.refresh, size: 16),
          label: const Text('Retry automatic discovery'),
        ),
      ],
    );
  }
}
