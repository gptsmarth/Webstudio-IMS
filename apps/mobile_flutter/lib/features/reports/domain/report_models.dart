import 'package:equatable/equatable.dart';

import 'report_date_presets.dart';

enum ReportType { inventory, sales, audit, tally }

extension ReportTypeApi on ReportType {
  String get previewPath => switch (this) {
        ReportType.inventory => '/api/v1/reports/inventory',
        ReportType.sales => '/api/v1/reports/sales',
        ReportType.audit => '/api/v1/reports/audit',
        ReportType.tally => '/api/v1/reports/notifications',
      };

  String get exportType => switch (this) {
        ReportType.tally => 'notification',
        _ => name,
      };

  String get label => switch (this) {
        ReportType.inventory => 'Inventory',
        ReportType.sales => 'Sales',
        ReportType.audit => 'Audit',
        ReportType.tally => 'Tally',
      };
}

const _tallyOutcomeToType = <String, String>{
  'processed': 'tally_sync_completed',
  'skipped': 'sync_failure',
  'duplicate': 'duplicate_sale',
  'missing_serial': 'serial_number_missing',
  'missing_model': 'product_model_missing',
  'model_mismatch': 'product_model_mismatch',
};

String? tallyOutcomeNotificationType(String outcome) {
  if (outcome.isEmpty) return null;
  return _tallyOutcomeToType[outcome];
}

class ReportQueryParams extends Equatable {
  const ReportQueryParams({
    this.page = 1,
    this.pageSize = 50,
    this.search = '',
    this.datePreset = '',
    this.dateFrom = '',
    this.dateTo = '',
    this.brandId,
    this.locationId,
    this.locationType = '',
    this.productModelId,
    this.serialNumber = '',
    this.inventoryStatus = '',
    this.color = '',
    this.userId,
    this.invoiceNumber = '',
    this.customerName = '',
    this.paymentMode = '',
    this.saleSource = '',
    this.auditAction = '',
    this.auditSource = '',
    this.actorRole = '',
    this.notificationType = '',
    this.syncStatus = '',
    this.tallyOutcome = '',
    this.company = '',
    this.sortField = '',
    this.sortDirection = 'desc',
  });

  final int page;
  final int pageSize;
  final String search;
  final String datePreset;
  final String dateFrom;
  final String dateTo;
  final int? brandId;
  final int? locationId;
  final String locationType;
  final String? productModelId;
  final String serialNumber;
  final String inventoryStatus;
  final String color;
  final int? userId;
  final String invoiceNumber;
  final String customerName;
  final String paymentMode;
  final String saleSource;
  final String auditAction;
  final String auditSource;
  final String actorRole;
  final String notificationType;
  final String syncStatus;
  final String tallyOutcome;
  final String company;
  final String sortField;
  final String sortDirection;

  Map<String, dynamic> toQueryParams(ReportType type) {
    final dateRange = resolveReportDateRange(datePreset, dateFrom, dateTo);
    final params = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      if (search.trim().isNotEmpty) 'search': search.trim(),
      if (brandId != null) 'brand_id': brandId,
      if (locationId != null) 'location_id': locationId,
      if (locationType.isNotEmpty) 'location_type': locationType,
      if (productModelId != null && productModelId!.isNotEmpty) 'product_model_id': productModelId,
      if (serialNumber.trim().isNotEmpty) 'serial_number': serialNumber.trim(),
      if (sortField.isNotEmpty) 'sort_field': sortField,
      if (sortDirection.isNotEmpty) 'sort_direction': sortDirection,
    };

    switch (type) {
      case ReportType.inventory:
        if (color.trim().isNotEmpty) params['color'] = color.trim();
        if (dateRange.from.isNotEmpty) params['date_from'] = dateRange.from;
        if (dateRange.to.isNotEmpty) params['date_to'] = dateRange.to;
        if (inventoryStatus == 'available') {
          params['status'] = 'available';
          params['is_archived'] = false;
        } else if (inventoryStatus == 'sold') {
          params['status'] = 'sold';
        } else if (inventoryStatus == 'archived') {
          params['is_archived'] = true;
        }
      case ReportType.sales:
        if (dateRange.from.isNotEmpty) params['date_from'] = dateRange.from;
        if (dateRange.to.isNotEmpty) params['date_to'] = dateRange.to;
        if (userId != null) params['user_id'] = userId;
        if (invoiceNumber.trim().isNotEmpty) params['invoice_number'] = invoiceNumber.trim();
        if (customerName.trim().isNotEmpty) params['customer_name'] = customerName.trim();
        if (paymentMode.trim().isNotEmpty) params['payment_mode'] = paymentMode.trim();
        if (saleSource.isNotEmpty) params['sale_source'] = saleSource;
      case ReportType.audit:
        if (dateRange.from.isNotEmpty) params['date_from'] = dateRange.from;
        if (dateRange.to.isNotEmpty) params['date_to'] = dateRange.to;
        if (userId != null) params['user_id'] = userId;
        if (auditAction.isNotEmpty) params['audit_action'] = auditAction;
        if (auditSource.isNotEmpty) params['audit_source'] = auditSource;
        if (actorRole.isNotEmpty) params['actor_role'] = actorRole;
      case ReportType.tally:
        params['notification_category'] = 'tally_sync';
        if (dateRange.from.isNotEmpty) params['date_from'] = dateRange.from;
        if (dateRange.to.isNotEmpty) params['date_to'] = dateRange.to;
        if (syncStatus.isNotEmpty) params['status'] = syncStatus;
        final outcomeType = tallyOutcomeNotificationType(tallyOutcome);
        if (outcomeType != null) {
          params['notification_type'] = outcomeType;
        } else if (notificationType.isNotEmpty) {
          params['notification_type'] = notificationType;
        }
        if (invoiceNumber.trim().isNotEmpty) {
          params['search'] = invoiceNumber.trim();
        } else if (company.trim().isNotEmpty) {
          params['search'] = company.trim();
        }
    }
    return params;
  }

  int activeFilterCount(ReportType type) {
    var count = 0;
    void bump(bool active) {
      if (active) count += 1;
    }

    bump(search.trim().isNotEmpty);
    bump(datePreset.isNotEmpty || dateFrom.isNotEmpty || dateTo.isNotEmpty);
    bump(brandId != null);
    bump(locationId != null);
    bump(locationType.isNotEmpty);
    bump(productModelId != null && productModelId!.isNotEmpty);
    bump(serialNumber.trim().isNotEmpty);

    switch (type) {
      case ReportType.inventory:
        bump(inventoryStatus.isNotEmpty);
        bump(color.trim().isNotEmpty);
      case ReportType.sales:
        bump(userId != null);
        bump(invoiceNumber.trim().isNotEmpty);
        bump(customerName.trim().isNotEmpty);
        bump(paymentMode.trim().isNotEmpty);
        bump(saleSource.isNotEmpty);
      case ReportType.audit:
        bump(userId != null);
        bump(auditAction.isNotEmpty);
        bump(auditSource.isNotEmpty);
        bump(actorRole.isNotEmpty);
      case ReportType.tally:
        bump(company.trim().isNotEmpty);
        bump(syncStatus.isNotEmpty);
        bump(tallyOutcome.isNotEmpty);
        bump(notificationType.isNotEmpty);
        bump(invoiceNumber.trim().isNotEmpty);
    }
    return count;
  }

  ReportQueryParams copyWith({
    int? page,
    int? pageSize,
    String? search,
    String? datePreset,
    String? dateFrom,
    String? dateTo,
    int? brandId,
    bool clearBrandId = false,
    int? locationId,
    bool clearLocationId = false,
    String? locationType,
    String? productModelId,
    bool clearProductModelId = false,
    String? serialNumber,
    String? inventoryStatus,
    String? color,
    int? userId,
    bool clearUserId = false,
    String? invoiceNumber,
    String? customerName,
    String? paymentMode,
    String? saleSource,
    String? auditAction,
    String? auditSource,
    String? actorRole,
    String? notificationType,
    String? syncStatus,
    String? tallyOutcome,
    String? company,
    String? sortField,
    String? sortDirection,
  }) {
    return ReportQueryParams(
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
      search: search ?? this.search,
      datePreset: datePreset ?? this.datePreset,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
      brandId: clearBrandId ? null : brandId ?? this.brandId,
      locationId: clearLocationId ? null : locationId ?? this.locationId,
      locationType: locationType ?? this.locationType,
      productModelId: clearProductModelId ? null : productModelId ?? this.productModelId,
      serialNumber: serialNumber ?? this.serialNumber,
      inventoryStatus: inventoryStatus ?? this.inventoryStatus,
      color: color ?? this.color,
      userId: clearUserId ? null : userId ?? this.userId,
      invoiceNumber: invoiceNumber ?? this.invoiceNumber,
      customerName: customerName ?? this.customerName,
      paymentMode: paymentMode ?? this.paymentMode,
      saleSource: saleSource ?? this.saleSource,
      auditAction: auditAction ?? this.auditAction,
      auditSource: auditSource ?? this.auditSource,
      actorRole: actorRole ?? this.actorRole,
      notificationType: notificationType ?? this.notificationType,
      syncStatus: syncStatus ?? this.syncStatus,
      tallyOutcome: tallyOutcome ?? this.tallyOutcome,
      company: company ?? this.company,
      sortField: sortField ?? this.sortField,
      sortDirection: sortDirection ?? this.sortDirection,
    );
  }

  @override
  List<Object?> get props => [
        page,
        search,
        datePreset,
        dateFrom,
        dateTo,
        brandId,
        locationId,
        locationType,
        productModelId,
        serialNumber,
        inventoryStatus,
        color,
        userId,
        invoiceNumber,
        customerName,
        paymentMode,
        saleSource,
        auditAction,
        auditSource,
        actorRole,
        notificationType,
        syncStatus,
        tallyOutcome,
        company,
      ];
}

class ReportPreviewResult extends Equatable {
  const ReportPreviewResult({
    required this.rows,
    required this.page,
    required this.pageSize,
    required this.totalItems,
    required this.totalPages,
    this.summary,
  });

  final List<Map<String, dynamic>> rows;
  final int page;
  final int pageSize;
  final int totalItems;
  final int totalPages;
  final Map<String, dynamic>? summary;

  @override
  List<Object?> get props => [rows.length, page, totalItems];
}

String reportCellValue(Map<String, dynamic> row, String key) {
  final value = row[key];
  if (value == null) return '—';
  if (value is bool) return value ? 'Yes' : 'No';
  return value.toString().split('T').first;
}

List<String> reportColumns(ReportType type) => switch (type) {
      ReportType.inventory => [
          'serial_number',
          'brand_name',
          'model_name',
          'location_name',
          'status',
          'created_at',
        ],
      ReportType.sales => [
          'invoice_number',
          'customer_name',
          'serial_number',
          'brand_name',
          'location_name',
          'sold_at',
        ],
      ReportType.audit => [
          'action',
          'entity_type',
          'actor_display_name',
          'serial_number',
          'created_at',
        ],
      ReportType.tally => [
          'notification_type',
          'title',
          'severity',
          'status',
          'created_at',
        ],
    };

Map<String, String> reportColumnLabels(ReportType type) => {
      for (final key in reportColumns(type))
        key: key.split('_').map((p) => p.isEmpty ? p : '${p[0].toUpperCase()}${p.substring(1)}').join(' '),
    };
