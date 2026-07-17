import 'package:equatable/equatable.dart';

import '../../inventory/domain/product_spec_lookup.dart';

/// Coerces the backend money fields (Decimal serialised as string|number|null).
double? _toNum(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString());
}

class PurchaseTaxBreakdown extends Equatable {
  const PurchaseTaxBreakdown({
    this.subtotal,
    this.discountAmount,
    this.roundOff,
    this.cgstAmount,
    this.sgstAmount,
    this.igstAmount,
    this.cessAmount,
    this.grandTotal,
  });

  final double? subtotal;
  final double? discountAmount;
  final double? roundOff;
  final double? cgstAmount;
  final double? sgstAmount;
  final double? igstAmount;
  final double? cessAmount;
  final double? grandTotal;

  factory PurchaseTaxBreakdown.fromJson(Map<String, dynamic> json) => PurchaseTaxBreakdown(
        subtotal: _toNum(json['subtotal']),
        discountAmount: _toNum(json['discount_amount']),
        roundOff: _toNum(json['round_off']),
        cgstAmount: _toNum(json['cgst_amount']),
        sgstAmount: _toNum(json['sgst_amount']),
        igstAmount: _toNum(json['igst_amount']),
        cessAmount: _toNum(json['cess_amount']),
        grandTotal: _toNum(json['grand_total']),
      );

  @override
  List<Object?> get props =>
      [subtotal, discountAmount, roundOff, cgstAmount, sgstAmount, igstAmount, cessAmount, grandTotal];
}

class PurchaseQueueItem extends Equatable {
  const PurchaseQueueItem({
    required this.id,
    this.supplierName,
    this.voucherDate,
    required this.voucherNumber,
    this.invoiceNumber,
    this.referenceNumber,
    required this.voucherGuid,
    this.voucherType,
    this.grandTotal,
    required this.taxes,
    required this.status,
    required this.groupCount,
    required this.importedGroupCount,
    required this.pendingGroupCount,
  });

  final int id;
  final String? supplierName;
  final String? voucherDate;
  final String voucherNumber;
  final String? invoiceNumber;
  final String? referenceNumber;
  final String voucherGuid;
  final String? voucherType;
  final double? grandTotal;
  final PurchaseTaxBreakdown taxes;
  final String status;
  final int groupCount;
  final int importedGroupCount;
  final int pendingGroupCount;

  factory PurchaseQueueItem.fromJson(Map<String, dynamic> json) => PurchaseQueueItem(
        id: (json['id'] as num).toInt(),
        supplierName: json['supplier_name'] as String?,
        voucherDate: json['voucher_date'] as String?,
        voucherNumber: json['voucher_number'] as String? ?? '',
        invoiceNumber: json['invoice_number'] as String?,
        referenceNumber: json['reference_number'] as String?,
        voucherGuid: json['voucher_guid'] as String? ?? '',
        voucherType: json['voucher_type'] as String?,
        grandTotal: _toNum(json['grand_total']),
        taxes: PurchaseTaxBreakdown.fromJson(
          (json['taxes'] as Map?)?.cast<String, dynamic>() ?? const {},
        ),
        status: json['status'] as String? ?? 'pending',
        groupCount: (json['group_count'] as num?)?.toInt() ?? 0,
        importedGroupCount: (json['imported_group_count'] as num?)?.toInt() ?? 0,
        pendingGroupCount: (json['pending_group_count'] as num?)?.toInt() ?? 0,
      );

  @override
  List<Object?> get props => [id, status, importedGroupCount];
}

class PurchaseSerialCell extends Equatable {
  const PurchaseSerialCell({
    required this.serialNumber,
    this.isDuplicate = false,
    this.existingStatus,
  });

  final String serialNumber;
  final bool isDuplicate;
  final String? existingStatus;

  factory PurchaseSerialCell.fromJson(Map<String, dynamic> json) => PurchaseSerialCell(
        serialNumber: json['serial_number'] as String? ?? '',
        isDuplicate: json['is_duplicate'] as bool? ?? false,
        existingStatus: json['existing_status'] as String?,
      );

  @override
  List<Object?> get props => [serialNumber, isDuplicate];
}

class PurchaseModelGroup extends Equatable {
  const PurchaseModelGroup({
    required this.groupKey,
    required this.stockItemName,
    required this.quantity,
    this.serialSource,
    required this.serials,
    this.lineTotal,
    this.imported = false,
    this.productModelId,
    this.duplicateCount = 0,
  });

  final String groupKey;
  final String stockItemName;
  final int quantity;
  final String? serialSource;
  final List<PurchaseSerialCell> serials;
  final double? lineTotal;
  final bool imported;
  final String? productModelId;
  final int duplicateCount;

  factory PurchaseModelGroup.fromJson(Map<String, dynamic> json) => PurchaseModelGroup(
        groupKey: json['group_key'] as String? ?? '',
        stockItemName: json['stock_item_name'] as String? ?? '',
        quantity: (json['quantity'] as num?)?.toInt() ?? 0,
        serialSource: json['serial_source'] as String?,
        serials: ((json['serials'] as List?) ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map((entry) => PurchaseSerialCell.fromJson(entry.cast<String, dynamic>()))
            .toList(),
        lineTotal: _toNum(json['line_total']),
        imported: json['imported'] as bool? ?? false,
        productModelId: json['product_model_id'] as String?,
        duplicateCount: (json['duplicate_count'] as num?)?.toInt() ?? 0,
      );

  @override
  List<Object?> get props => [groupKey, imported, quantity];
}

class PurchaseVoucherDetail extends Equatable {
  const PurchaseVoucherDetail({
    required this.id,
    this.supplierName,
    this.voucherDate,
    required this.voucherNumber,
    this.invoiceNumber,
    this.referenceNumber,
    required this.voucherGuid,
    this.voucherType,
    this.narration,
    required this.taxes,
    this.grandTotal,
    required this.status,
    required this.groups,
  });

  final int id;
  final String? supplierName;
  final String? voucherDate;
  final String voucherNumber;
  final String? invoiceNumber;
  final String? referenceNumber;
  final String voucherGuid;
  final String? voucherType;
  final String? narration;
  final PurchaseTaxBreakdown taxes;
  final double? grandTotal;
  final String status;
  final List<PurchaseModelGroup> groups;

  factory PurchaseVoucherDetail.fromJson(Map<String, dynamic> json) => PurchaseVoucherDetail(
        id: (json['id'] as num).toInt(),
        supplierName: json['supplier_name'] as String?,
        voucherDate: json['voucher_date'] as String?,
        voucherNumber: json['voucher_number'] as String? ?? '',
        invoiceNumber: json['invoice_number'] as String?,
        referenceNumber: json['reference_number'] as String?,
        voucherGuid: json['voucher_guid'] as String? ?? '',
        voucherType: json['voucher_type'] as String?,
        narration: json['narration'] as String?,
        taxes: PurchaseTaxBreakdown.fromJson(
          (json['taxes'] as Map?)?.cast<String, dynamic>() ?? const {},
        ),
        grandTotal: _toNum(json['grand_total']),
        status: json['status'] as String? ?? 'pending',
        groups: ((json['groups'] as List?) ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map((entry) => PurchaseModelGroup.fromJson(entry.cast<String, dynamic>()))
            .toList(),
      );

  @override
  List<Object?> get props => [id, status, groups];
}

class MatchedModel extends Equatable {
  const MatchedModel({
    required this.id,
    required this.modelNumber,
    required this.modelName,
    required this.category,
    required this.isActive,
    this.matchKind = 'exact',
  });

  final String id;
  final String modelNumber;
  final String modelName;
  final String category;
  final bool isActive;

  /// 'exact' — normalized model number matches exactly (auto-selectable).
  /// 'partial' — one model number contains the other (a suggestion the operator
  /// must confirm, e.g. an IMS entry with an extra base-model suffix).
  final String matchKind;

  bool get isPartial => matchKind == 'partial';

  factory MatchedModel.fromJson(Map<String, dynamic> json) => MatchedModel(
        id: json['id'] as String,
        modelNumber: json['model_number'] as String? ?? '',
        modelName: json['model_name'] as String? ?? '',
        category: json['category'] as String? ?? 'laptop',
        isActive: json['is_active'] as bool? ?? true,
        matchKind: json['match_kind'] as String? ?? 'exact',
      );

  @override
  List<Object?> get props => [id];
}

class MatchModelResponse extends Equatable {
  const MatchModelResponse({
    required this.normalizedModelNumber,
    required this.matches,
    this.autoSelectedModelId,
  });

  final String normalizedModelNumber;
  final List<MatchedModel> matches;
  final String? autoSelectedModelId;

  factory MatchModelResponse.fromJson(Map<String, dynamic> json) => MatchModelResponse(
        normalizedModelNumber: json['normalized_model_number'] as String? ?? '',
        matches: ((json['matches'] as List?) ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map((entry) => MatchedModel.fromJson(entry.cast<String, dynamic>()))
            .toList(),
        autoSelectedModelId: json['auto_selected_model_id'] as String?,
      );

  @override
  List<Object?> get props => [normalizedModelNumber, matches, autoSelectedModelId];
}

class AccessoryMatch extends Equatable {
  const AccessoryMatch({
    required this.id,
    required this.modelNumber,
    required this.modelName,
    this.partNumber,
    this.accessoryKind,
    required this.category,
    required this.isActive,
    required this.score,
  });

  final String id;
  final String modelNumber;
  final String modelName;
  final String? partNumber;
  final String? accessoryKind;
  final String category;
  final bool isActive;
  final double score;

  factory AccessoryMatch.fromJson(Map<String, dynamic> json) => AccessoryMatch(
        id: json['id'] as String,
        modelNumber: json['model_number'] as String? ?? '',
        modelName: json['model_name'] as String? ?? '',
        partNumber: json['part_number'] as String?,
        accessoryKind: json['accessory_kind'] as String?,
        category: json['category'] as String? ?? 'accessory',
        isActive: json['is_active'] as bool? ?? true,
        score: _toNum(json['score']) ?? 0,
      );

  @override
  List<Object?> get props => [id, score];
}

class MatchAccessoryResponse extends Equatable {
  const MatchAccessoryResponse({
    required this.normalizedQuery,
    required this.matches,
    this.autoSelectedModelId,
  });

  final String normalizedQuery;
  final List<AccessoryMatch> matches;
  final String? autoSelectedModelId;

  factory MatchAccessoryResponse.fromJson(Map<String, dynamic> json) => MatchAccessoryResponse(
        normalizedQuery: json['normalized_query'] as String? ?? '',
        matches: ((json['matches'] as List?) ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map((entry) => AccessoryMatch.fromJson(entry.cast<String, dynamic>()))
            .toList(),
        autoSelectedModelId: json['auto_selected_model_id'] as String?,
      );

  @override
  List<Object?> get props => [normalizedQuery, matches, autoSelectedModelId];
}

class PurchaseImportRequest {
  const PurchaseImportRequest({
    required this.voucherId,
    required this.groupKey,
    required this.brandId,
    required this.mode,
    this.productModelId,
    this.newProductModel,
    required this.serialNumbers,
    required this.color,
    required this.currentLocationId,
    this.status = 'available',
    this.purchasePrice,
  });

  final int voucherId;
  final String groupKey;
  final int brandId;
  final String mode;
  final String? productModelId;
  final Map<String, dynamic>? newProductModel;
  final List<String> serialNumbers;
  final String color;
  final int currentLocationId;
  final String status;
  final double? purchasePrice;

  Map<String, dynamic> toJson() => {
        'voucher_id': voucherId,
        'group_key': groupKey,
        'brand_id': brandId,
        'mode': mode,
        if (productModelId != null) 'product_model_id': productModelId,
        if (newProductModel != null) 'new_product_model': newProductModel,
        'serial_numbers': serialNumbers,
        'color': color,
        'current_location_id': currentLocationId,
        'status': status,
        if (purchasePrice != null) 'purchase_price': purchasePrice,
      };

  /// Builds the import request for the "new model" path from the shared wizard
  /// request shape, so mobile reuses the exact desktop contract.
  factory PurchaseImportRequest.fromWizard({
    required int voucherId,
    required String groupKey,
    required AddLaptopWizardRequest wizard,
    required String status,
  }) {
    final units = wizard.units;
    final first = units.isNotEmpty ? units.first : null;
    return PurchaseImportRequest(
      voucherId: voucherId,
      groupKey: groupKey,
      brandId: wizard.brandId,
      mode: 'new',
      newProductModel: wizard.newProductModel,
      serialNumbers: units.map((u) => u.serialNumber.trim()).where((s) => s.isNotEmpty).toList(),
      color: first?.color ?? 'Not specified',
      currentLocationId: first?.currentLocationId ?? 0,
      status: status,
      purchasePrice: first?.purchasePrice,
    );
  }
}

class PurchaseImportResult extends Equatable {
  const PurchaseImportResult({
    required this.productModelId,
    required this.importedCount,
    required this.voucherStatus,
    required this.groupKey,
    required this.existingModel,
  });

  final String productModelId;
  final int importedCount;
  final String voucherStatus;
  final String groupKey;
  final bool existingModel;

  factory PurchaseImportResult.fromJson(Map<String, dynamic> json) => PurchaseImportResult(
        productModelId: json['product_model_id'] as String? ?? '',
        importedCount: (json['imported_count'] as num?)?.toInt() ?? 0,
        voucherStatus: json['voucher_status'] as String? ?? 'pending',
        groupKey: json['group_key'] as String? ?? '',
        existingModel: json['existing_model'] as bool? ?? false,
      );

  @override
  List<Object?> get props => [productModelId, importedCount, voucherStatus];
}

class PurchaseBackfillResult extends Equatable {
  const PurchaseBackfillResult({
    required this.fetched,
    required this.newCount,
    required this.fromDate,
    this.toDate,
  });

  final int fetched;
  final int newCount;
  final String fromDate;
  final String? toDate;

  factory PurchaseBackfillResult.fromJson(Map<String, dynamic> json) => PurchaseBackfillResult(
        fetched: (json['fetched'] as num?)?.toInt() ?? 0,
        newCount: (json['new'] as num?)?.toInt() ?? 0,
        fromDate: json['from_date'] as String? ?? '',
        toDate: json['to_date'] as String?,
      );

  @override
  List<Object?> get props => [fetched, newCount, fromDate, toDate];
}
