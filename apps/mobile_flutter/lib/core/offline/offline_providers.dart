import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/dashboard/data/dashboard_repository.dart';
import '../../features/inventory/data/inventory_repository.dart';
import '../network/api_client.dart';
import '../network/connectivity_provider.dart';
import 'api_cache_service.dart';
import 'conflict_detector.dart';
import 'offline_cache_store.dart';
import 'offline_dashboard_service.dart';
import 'offline_inventory_service.dart';
import 'offline_models.dart';
import 'pending_operations_store.dart';
import 'retry_queue.dart';
import 'sync_state_repository.dart';

class BackgroundSyncCoordinator extends StateNotifier<SyncWorkspaceState> {
  BackgroundSyncCoordinator(this._ref) : super(const SyncWorkspaceState()) {
    _refreshCounts();
  }

  final Ref _ref;
  Timer? _pollTimer;
  bool _started = false;

  SyncStateRepository get _syncState => _ref.read(syncStateRepositoryProvider);
  PendingOperationsStore get _pending => _ref.read(pendingOperationsStoreProvider);
  OfflineInventoryService get _inventoryOffline => _ref.read(offlineInventoryServiceProvider);
  OfflineDashboardService get _dashboardOffline => _ref.read(offlineDashboardServiceProvider);
  RetryQueue get _retryQueue => _ref.read(retryQueueProvider);

  void start() {
    if (_started) return;
    _started = true;
    _refreshCounts();
    unawaited(syncNow());
  }

  void stop() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _started = false;
  }

  Future<void> syncNow() async {
    final online = _ref.read(networkStatusProvider);
    if (!online) {
      state = state.copyWith(isStale: true, clearError: true);
      _refreshCounts();
      return;
    }

    state = state.copyWith(syncing: true, clearError: true);
    try {
      final previous = _syncState.readLocal();
      final remote = await _syncState.fetchRemote();
      final entityChanged = remote.hasEntityChanges(previous);

      final retryResult = await _retryQueue.processAll();
      if (entityChanged || retryResult.applied > 0) {
        await _inventoryOffline.loadWorkspace(forceRefresh: true);
        await _dashboardOffline.loadDashboard(forceRefresh: true);
        _ref.invalidate(offlineDashboardBundleProvider);
      }

      _schedulePoll(remote.pollIntervalSeconds);
      state = state.copyWith(
        syncing: false,
        lastSyncAt: DateTime.now(),
        lastSyncState: remote,
        isStale: false,
        pendingCount: _pending.count,
        conflictCount: _pending.conflictCount,
      );
    } catch (error) {
      state = state.copyWith(
        syncing: false,
        lastError: error.toString(),
        isStale: true,
        pendingCount: _pending.count,
        conflictCount: _pending.conflictCount,
      );
    }
  }

  Future<void> enqueuePending(PendingOperation operation) async {
    await _pending.enqueue(operation);
    _refreshCounts();
  }

  void _schedulePoll(int seconds) {
    _pollTimer?.cancel();
    _pollTimer = Timer(Duration(seconds: seconds.clamp(30, 300)), () => unawaited(syncNow()));
  }

  void _refreshCounts() {
    state = state.copyWith(
      pendingCount: _pending.count,
      conflictCount: _pending.conflictCount,
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final offlineCacheStoreProvider = Provider<OfflineCacheStore>((ref) => OfflineCacheStore());

final apiCacheServiceProvider = Provider<ApiCacheService>((ref) => ApiCacheService());

final pendingOperationsStoreProvider = Provider<PendingOperationsStore>((ref) => PendingOperationsStore());

final conflictDetectorProvider = Provider<ConflictDetector>((ref) => const ConflictDetector());

final syncStateRepositoryProvider = Provider<SyncStateRepository>((ref) {
  return SyncStateRepository(
    ref.watch(apiClientProvider),
    ref.watch(offlineCacheStoreProvider),
  );
});

final networkStatusProvider = Provider<bool>((ref) {
  return ref.watch(connectivityProvider).maybeWhen(data: (value) => value, orElse: () => true);
});

final offlineInventoryServiceProvider = Provider<OfflineInventoryService>((ref) {
  return OfflineInventoryService(
    inventory: ref.watch(inventoryRepositoryProvider),
    dashboard: ref.watch(dashboardRepositoryProvider),
    cache: ref.watch(offlineCacheStoreProvider),
    isOnline: () => ref.read(networkStatusProvider),
  );
});

final offlineDashboardServiceProvider = Provider<OfflineDashboardService>((ref) {
  return OfflineDashboardService(
    dashboard: ref.watch(dashboardRepositoryProvider),
    cache: ref.watch(offlineCacheStoreProvider),
    isOnline: () => ref.read(networkStatusProvider),
  );
});

final retryQueueProvider = Provider<RetryQueue>((ref) {
  return RetryQueue(
    store: ref.watch(pendingOperationsStoreProvider),
    inventory: ref.watch(inventoryRepositoryProvider),
    conflicts: ref.watch(conflictDetectorProvider),
  );
});

final backgroundSyncCoordinatorProvider =
    StateNotifierProvider<BackgroundSyncCoordinator, SyncWorkspaceState>((ref) {
  return BackgroundSyncCoordinator(ref);
});

final offlineDashboardBundleProvider = FutureProvider.autoDispose<OfflineLoadResult<DashboardCacheBundle>>((ref) async {
  return ref.watch(offlineDashboardServiceProvider).loadDashboard();
});
