import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/catalogue/domain/catalogue_models.dart';
import 'package:webstudio_ims/features/inventory/presentation/inventory_controller.dart';

void main() {
  test('AsusPriceRefreshStatus.fromJson parses the backend envelope', () {
    final status = AsusPriceRefreshStatus.fromJson({
      'total': 76,
      'completed': 42,
      'in_progress': 34,
      'started_at': '2026-09-12T10:00:00Z',
      'finished_at': null,
    });

    expect(status.total, 76);
    expect(status.completed, 42);
    expect(status.inProgress, 34);
    expect(status.startedAt, '2026-09-12T10:00:00Z');
    expect(status.finishedAt, isNull);
  });

  test('asusPriceRunMessage shows live progress while a run is in flight', () {
    const workspace = InventoryWorkspaceState(
      asusPriceRunStatus: AsusPriceRefreshStatus(
        total: 76,
        completed: 42,
        inProgress: 34,
        startedAt: '2026-09-12T10:00:00Z',
        finishedAt: null,
      ),
    );

    expect(workspace.asusPriceRunMessage, 'Refreshing ASUS prices — 42 of 76 done…');
    expect(workspace.asusPriceRunShowsDismiss, isFalse);
  });

  test('asusPriceRunMessage shows completion and dismiss once finished and unseen', () {
    const workspace = InventoryWorkspaceState(
      asusPriceRunStatus: AsusPriceRefreshStatus(
        total: 76,
        completed: 76,
        inProgress: 0,
        startedAt: '2026-09-12T10:00:00Z',
        finishedAt: '2026-09-12T10:15:00Z',
      ),
    );

    expect(workspace.asusPriceRunMessage, 'Done — refreshed 76 ASUS model(s).');
    expect(workspace.asusPriceRunShowsDismiss, isTrue);
  });

  test('a dismissed run shows neither a message nor the dismiss button again', () {
    const workspace = InventoryWorkspaceState(
      asusPriceRunStatus: AsusPriceRefreshStatus(
        total: 76,
        completed: 76,
        inProgress: 0,
        startedAt: '2026-09-12T10:00:00Z',
        finishedAt: '2026-09-12T10:15:00Z',
      ),
      asusPriceRunDismissedAt: '2026-09-12T10:15:00Z',
    );

    expect(workspace.asusPriceRunMessage, isNull);
    expect(workspace.asusPriceRunShowsDismiss, isFalse);
  });

  test('no run yet shows nothing', () {
    const workspace = InventoryWorkspaceState();
    expect(workspace.asusPriceRunMessage, isNull);
    expect(workspace.asusPriceRunShowsDismiss, isFalse);
  });
}
