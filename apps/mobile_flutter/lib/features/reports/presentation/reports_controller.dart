import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../data/report_repository.dart';
import '../domain/report_models.dart';
import '../../../shared/models/downloaded_file.dart';

class ReportsWorkspaceState {
  const ReportsWorkspaceState({
    this.reportType = ReportType.inventory,
    this.params = const ReportQueryParams(),
    this.preview,
    this.loading = false,
    this.error,
    this.hasPreviewed = false,
  });

  final ReportType reportType;
  final ReportQueryParams params;
  final ReportPreviewResult? preview;
  final bool loading;
  final String? error;
  final bool hasPreviewed;

  ReportsWorkspaceState copyWith({
    ReportType? reportType,
    ReportQueryParams? params,
    ReportPreviewResult? preview,
    bool? loading,
    String? error,
    bool? hasPreviewed,
    bool clearPreview = false,
    bool clearError = false,
  }) {
    return ReportsWorkspaceState(
      reportType: reportType ?? this.reportType,
      params: params ?? this.params,
      preview: clearPreview ? null : preview ?? this.preview,
      loading: loading ?? this.loading,
      error: clearError ? null : error ?? this.error,
      hasPreviewed: hasPreviewed ?? this.hasPreviewed,
    );
  }
}

final reportsWorkspaceProvider =
    StateNotifierProvider<ReportsWorkspaceController, ReportsWorkspaceState>((ref) {
  return ReportsWorkspaceController(ref);
});

class ReportsWorkspaceController extends StateNotifier<ReportsWorkspaceState> {
  ReportsWorkspaceController(this._ref) : super(const ReportsWorkspaceState());

  final Ref _ref;

  ReportRepository get _reports => _ref.read(reportRepositoryProvider);

  void setReportType(ReportType type) {
    if (state.reportType == type) return;
    state = state.copyWith(
      reportType: type,
      params: const ReportQueryParams(),
      clearPreview: true,
      hasPreviewed: false,
      clearError: true,
    );
    preview();
  }

  void setParams(ReportQueryParams params) => state = state.copyWith(params: params);
  void setSearch(String value) => state = state.copyWith(params: state.params.copyWith(search: value, page: 1));

  void applyFilters(ReportQueryParams params) {
    state = state.copyWith(
      params: params,
      clearPreview: true,
      hasPreviewed: false,
      clearError: true,
    );
    preview();
  }

  void resetFilters() {
    state = state.copyWith(
      params: const ReportQueryParams(),
      clearPreview: true,
      hasPreviewed: false,
      clearError: true,
    );
  }

  Future<void> preview() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final result = await _reports.preview(state.reportType, state.params);
      state = state.copyWith(loading: false, preview: result, hasPreviewed: true);
    } catch (error) {
      state = state.copyWith(loading: false, error: _errorMessage(error));
    }
  }

  Future<void> setPage(int page) async {
    state = state.copyWith(params: state.params.copyWith(page: page));
    if (state.hasPreviewed) await preview();
  }

  Future<void> refresh() async {
    if (state.hasPreviewed) await preview();
  }

  Future<DownloadedFile?> fetchExport({String format = 'xlsx'}) async {
    if (!state.hasPreviewed) {
      state = state.copyWith(error: 'Preview the report before exporting.');
      return null;
    }
    state = state.copyWith(loading: true, clearError: true);
    try {
      final file = await _reports.exportReport(state.reportType, state.params, format: format);
      state = state.copyWith(loading: false);
      return file;
    } catch (error) {
      state = state.copyWith(loading: false, error: _errorMessage(error));
      return null;
    }
  }

  String _errorMessage(Object error) {
    if (error is ApiException) return error.message;
    return error.toString();
  }
}
