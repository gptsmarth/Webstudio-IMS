enum PendingOperationType { transferLocation, markSold, createInventory }

enum SyncConflictKind { entityUpdatedOnServer, duplicateSerial }

class CachedPayload<T> {
  const CachedPayload({
    required this.data,
    required this.cachedAt,
  });

  final T data;
  final DateTime cachedAt;

  bool isOlderThan(Duration maxAge) => DateTime.now().difference(cachedAt) > maxAge;
}

class OfflineLoadResult<T> {
  const OfflineLoadResult({
    required this.data,
    this.fromCache = false,
    this.isStale = false,
    this.error,
  });

  final T data;
  final bool fromCache;
  final bool isStale;
  final String? error;
}

class SyncConflict {
  const SyncConflict({
    required this.kind,
    required this.message,
    this.serverUpdatedAt,
    this.localUpdatedAt,
  });

  final SyncConflictKind kind;
  final String message;
  final String? serverUpdatedAt;
  final String? localUpdatedAt;

  Map<String, dynamic> toJson() => {
        'kind': kind.name,
        'message': message,
        if (serverUpdatedAt != null) 'server_updated_at': serverUpdatedAt,
        if (localUpdatedAt != null) 'local_updated_at': localUpdatedAt,
      };

  factory SyncConflict.fromJson(Map<String, dynamic> json) => SyncConflict(
        kind: SyncConflictKind.values.firstWhere(
          (k) => k.name == json['kind'],
          orElse: () => SyncConflictKind.entityUpdatedOnServer,
        ),
        message: json['message'] as String? ?? 'Conflict detected',
        serverUpdatedAt: json['server_updated_at'] as String?,
        localUpdatedAt: json['local_updated_at'] as String?,
      );
}

class PendingOperation {
  const PendingOperation({
    required this.id,
    required this.type,
    required this.payload,
    required this.createdAt,
    this.attemptCount = 0,
    this.lastError,
    this.conflict,
    this.entityId,
    this.entityUpdatedAt,
  });

  final String id;
  final PendingOperationType type;
  final Map<String, dynamic> payload;
  final DateTime createdAt;
  final int attemptCount;
  final String? lastError;
  final SyncConflict? conflict;
  final String? entityId;
  final String? entityUpdatedAt;

  bool get hasConflict => conflict != null;

  PendingOperation copyWith({
    int? attemptCount,
    String? lastError,
    SyncConflict? conflict,
    bool clearConflict = false,
    bool clearError = false,
  }) {
    return PendingOperation(
      id: id,
      type: type,
      payload: payload,
      createdAt: createdAt,
      attemptCount: attemptCount ?? this.attemptCount,
      lastError: clearError ? null : lastError ?? this.lastError,
      conflict: clearConflict ? null : conflict ?? this.conflict,
      entityId: entityId,
      entityUpdatedAt: entityUpdatedAt,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type.name,
        'payload': payload,
        'created_at': createdAt.toUtc().toIso8601String(),
        'attempt_count': attemptCount,
        if (lastError != null) 'last_error': lastError,
        if (conflict != null) 'conflict': conflict!.toJson(),
        if (entityId != null) 'entity_id': entityId,
        if (entityUpdatedAt != null) 'entity_updated_at': entityUpdatedAt,
      };

  factory PendingOperation.fromJson(Map<String, dynamic> json) => PendingOperation(
        id: json['id'] as String,
        type: PendingOperationType.values.firstWhere((t) => t.name == json['type']),
        payload: Map<String, dynamic>.from(json['payload'] as Map),
        createdAt: DateTime.parse(json['created_at'] as String),
        attemptCount: json['attempt_count'] as int? ?? 0,
        lastError: json['last_error'] as String?,
        conflict: json['conflict'] is Map<String, dynamic>
            ? SyncConflict.fromJson(json['conflict'] as Map<String, dynamic>)
            : null,
        entityId: json['entity_id'] as String?,
        entityUpdatedAt: json['entity_updated_at'] as String?,
      );
}

class SyncStateSnapshot {
  const SyncStateSnapshot({
    required this.serverTime,
    required this.syncToken,
    required this.highWaterMarks,
    required this.pollIntervalSeconds,
    required this.fetchedAt,
  });

  final String serverTime;
  final String syncToken;
  final Map<String, String?> highWaterMarks;
  final int pollIntervalSeconds;
  final DateTime fetchedAt;

  Map<String, dynamic> toJson() => {
        'server_time': serverTime,
        'sync_token': syncToken,
        'high_water_marks': highWaterMarks,
        'poll_interval_seconds': pollIntervalSeconds,
        'fetched_at': fetchedAt.toUtc().toIso8601String(),
      };

  factory SyncStateSnapshot.fromApi(Map<String, dynamic> json) {
    final marks = json['high_water_marks'];
    return SyncStateSnapshot(
      serverTime: json['server_time'] as String? ?? '',
      syncToken: json['sync_token'] as String? ?? '',
      highWaterMarks: marks is Map
          ? marks.map((key, value) => MapEntry(key.toString(), value?.toString()))
          : const {},
      pollIntervalSeconds: json['poll_interval_seconds'] as int? ?? 60,
      fetchedAt: DateTime.now().toUtc(),
    );
  }

  factory SyncStateSnapshot.fromJson(Map<String, dynamic> json) => SyncStateSnapshot(
        serverTime: json['server_time'] as String? ?? '',
        syncToken: json['sync_token'] as String? ?? '',
        highWaterMarks: (json['high_water_marks'] as Map?)?.map(
              (key, value) => MapEntry(key.toString(), value?.toString()),
            ) ??
            const {},
        pollIntervalSeconds: json['poll_interval_seconds'] as int? ?? 60,
        fetchedAt: DateTime.parse(json['fetched_at'] as String),
      );

  bool hasEntityChanges(SyncStateSnapshot? previous) {
    if (previous == null) return true;
    for (final entry in highWaterMarks.entries) {
      if (previous.highWaterMarks[entry.key] != entry.value) return true;
    }
    return false;
  }
}

class SyncWorkspaceState {
  const SyncWorkspaceState({
    this.syncing = false,
    this.lastSyncAt,
    this.lastError,
    this.pendingCount = 0,
    this.conflictCount = 0,
    this.isStale = false,
    this.lastSyncState,
  });

  final bool syncing;
  final DateTime? lastSyncAt;
  final String? lastError;
  final int pendingCount;
  final int conflictCount;
  final bool isStale;
  final SyncStateSnapshot? lastSyncState;

  SyncWorkspaceState copyWith({
    bool? syncing,
    DateTime? lastSyncAt,
    String? lastError,
    int? pendingCount,
    int? conflictCount,
    bool? isStale,
    SyncStateSnapshot? lastSyncState,
    bool clearError = false,
  }) {
    return SyncWorkspaceState(
      syncing: syncing ?? this.syncing,
      lastSyncAt: lastSyncAt ?? this.lastSyncAt,
      lastError: clearError ? null : lastError ?? this.lastError,
      pendingCount: pendingCount ?? this.pendingCount,
      conflictCount: conflictCount ?? this.conflictCount,
      isStale: isStale ?? this.isStale,
      lastSyncState: lastSyncState ?? this.lastSyncState,
    );
  }
}
