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
  Timer? _syncSuccessTimer;
  bool _started = false;
  bool _syncInProgress = false;

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

  /// [showBanner] — when true, show the full "Syncing…" banner (manual refresh).
  /// Background polls stay silent unless there are pending offline operations.
  Future<void> syncNow({bool showBanner = false}) async {
    if (_syncInProgress) return;

    final online = _ref.read(networkStatusProvider);
    if (!online) {
      state = state.copyWith(isStale: true, clearError: true, syncSuccessVisible: false, clearSyncProgress: true);
      _refreshCounts();
      return;
    }

    final pendingAtStart = _pending.count;
    final showProgress = showBanner || pendingAtStart > 0;
    _syncInProgress = true;
    if (showProgress) {
      state = state.copyWith(
        syncing: true,
        clearError: true,
        syncSuccessVisible: false,
        syncTotal: pendingAtStart,
        syncCompleted: 0,
      );
    }

    try {
      final previous = _syncState.readLocal();
      final remote = await _syncState.fetchRemote();
      final entityChanged = remote.hasInventoryEntityChanges(previous);

      var syncedCount = 0;
      final retryResult = await _retryQueue.processAll(
        onProgress: (completed, total) {
          if (!showProgress) return;
          syncedCount = completed;
          state = state.copyWith(syncCompleted: completed, syncTotal: total > 0 ? total : pendingAtStart);
        },
      );
      if (entityChanged || retryResult.applied > 0) {
        await _inventoryOffline.loadWorkspace(forceRefresh: true);
        await _dashboardOffline.loadDashboard(forceRefresh: true);
        _ref.invalidate(offlineDashboardBundleProvider);
      }

      _schedulePoll(remote.pollIntervalSeconds);
      final applied = retryResult.applied;
      state = state.copyWith(
        syncing: false,
        lastSyncAt: DateTime.now(),
        lastSyncState: remote,
        isStale: false,
        pendingCount: _pending.count,
        conflictCount: _pending.conflictCount,
        syncCompleted: applied > 0 ? applied : syncedCount,
        syncTotal: pendingAtStart > 0 ? pendingAtStart : (syncedCount > 0 ? syncedCount : 0),
        syncSuccessVisible: pendingAtStart > 0 && retryResult.failed == 0 && applied > 0,
      );
      if (state.syncSuccessVisible) {
        _syncSuccessTimer?.cancel();
        _syncSuccessTimer = Timer(const Duration(seconds: 4), () {
          state = state.copyWith(syncSuccessVisible: false, clearSyncProgress: true);
        });
      }
    } catch (error) {
      state = state.copyWith(
        syncing: false,
        lastError: error.toString(),
        isStale: true,
        pendingCount: _pending.count,
        conflictCount: _pending.conflictCount,
        syncSuccessVisible: false,
      );
    } finally {
      _syncInProgress = false;
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
    _syncSuccessTimer?.cancel();
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
