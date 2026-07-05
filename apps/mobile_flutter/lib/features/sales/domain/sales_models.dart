import 'package:equatable/equatable.dart';

enum SalesSortField {
  soldAt,
  invoiceNumber,
  customerName,
  serialNumber,
  brandName,
  modelName,
  locationName,
  paymentMode,
  saleSource,
}

extension SalesSortFieldApi on SalesSortField {
  String get apiName => switch (this) {
        SalesSortField.soldAt => 'sold_at',
        SalesSortField.invoiceNumber => 'invoice_number',
        SalesSortField.customerName => 'customer_name',
        SalesSortField.serialNumber => 'serial_number',
        SalesSortField.brandName => 'brand_name',
        SalesSortField.modelName => 'model_name',
        SalesSortField.locationName => 'location_name',
        SalesSortField.paymentMode => 'payment_mode',
        SalesSortField.saleSource => 'sale_source',
      };
}

class SaleListItem extends Equatable {
  const SaleListItem({
    required this.id,
    required this.inventoryItemId,
    required this.serialNumber,
    required this.brandName,
    required this.modelNumber,
    required this.modelName,
    required this.locationName,
    required this.invoiceNumber,
    this.customerName,
    this.paymentMode,
    this.saleAmount,
    this.saleAmountExcludingGst,
    required this.saleSource,
    required this.soldAt,
    this.recordedByUserId,
    this.recordedByDisplayName,
  });

  final int id;
  final String? inventoryItemId;
  final String serialNumber;
  final String brandName;
  final String modelNumber;
  final String modelName;
  final String locationName;
  final String invoiceNumber;
  final String? customerName;
  final String? paymentMode;
  final double? saleAmount;
  final double? saleAmountExcludingGst;
  final String saleSource;
  final String soldAt;
  final int? recordedByUserId;
  final String? recordedByDisplayName;

  factory SaleListItem.fromJson(Map<String, dynamic> json) => SaleListItem(
        id: json['id'] as int,
        inventoryItemId: json['inventory_item_id'] as String?,
        serialNumber: json['serial_number'] as String,
        brandName: json['brand_name'] as String,
        modelNumber: json['model_number'] as String,
        modelName: json['model_name'] as String,
        locationName: json['location_name'] as String,
        invoiceNumber: json['invoice_number'] as String,
        customerName: json['customer_name'] as String?,
        paymentMode: json['payment_mode'] as String?,
        saleAmount: (json['sale_amount'] as num?)?.toDouble(),
        saleAmountExcludingGst: (json['sale_amount_excluding_gst'] as num?)?.toDouble(),
        saleSource: json['sale_source'] as String,
        soldAt: json['sold_at'] as String,
        recordedByUserId: json['recorded_by_user_id'] as int?,
        recordedByDisplayName: json['recorded_by_display_name'] as String?,
      );

  @override
  List<Object?> get props => [id, invoiceNumber, serialNumber];
}

class SaleDetail extends Equatable {
  const SaleDetail({
    required this.id,
    required this.inventoryItemId,
    required this.serialNumber,
    required this.brandId,
    required this.brandName,
    required this.productModelId,
    required this.modelNumber,
    required this.modelName,
    required this.locationId,
    required this.locationName,
    required this.color,
    required this.cpu,
    required this.ramGb,
    required this.storageValue,
    required this.storageUnit,
    required this.storageType,
    required this.invoiceNumber,
    this.customerName,
    this.paymentMode,
    this.saleAmount,
    this.saleAmountExcludingGst,
    required this.saleSource,
    required this.soldAt,
    this.recordedByUserId,
    this.recordedByDisplayName,
    this.notes,
    this.tallyCompanyName,
    this.tallyVoucherNumber,
    this.printedInvoiceNumber,
    this.tallyVoucherType,
    required this.createdAt,
  });

  final int id;
  final String? inventoryItemId;
  final String serialNumber;
  final int? brandId;
  final String brandName;
  final String? productModelId;
  final String modelNumber;
  final String modelName;
  final int? locationId;
  final String locationName;
  final String color;
  final String cpu;
  final int? ramGb;
  final String storageValue;
  final String storageUnit;
  final String storageType;
  final String invoiceNumber;
  final String? customerName;
  final String? paymentMode;
  final double? saleAmount;
  final double? saleAmountExcludingGst;
  final String saleSource;
  final String soldAt;
  final int? recordedByUserId;
  final String? recordedByDisplayName;
  final String? notes;
  final String? tallyCompanyName;
  final String? tallyVoucherNumber;
  final String? printedInvoiceNumber;
  final String? tallyVoucherType;
  final String createdAt;

  String get specsLabel {
    final ram = ramGb != null ? '${ramGb}GB RAM' : 'RAM —';
    return '$cpu • $ram • $storageValue $storageUnit $storageType';
  }

  factory SaleDetail.fromJson(Map<String, dynamic> json) => SaleDetail(
        id: json['id'] as int,
        inventoryItemId: json['inventory_item_id'] as String?,
        serialNumber: json['serial_number'] as String,
        brandId: json['brand_id'] as int?,
        brandName: json['brand_name'] as String,
        productModelId: json['product_model_id'] as String?,
        modelNumber: json['model_number'] as String,
        modelName: json['model_name'] as String,
        locationId: json['location_id'] as int?,
        locationName: json['location_name'] as String,
        color: json['color'] as String? ?? '',
        cpu: json['cpu'] as String? ?? '',
        ramGb: json['ram_gb'] as int?,
        storageValue: json['storage_value']?.toString() ?? '',
        storageUnit: json['storage_unit'] as String? ?? '',
        storageType: json['storage_type'] as String? ?? '',
        invoiceNumber: json['invoice_number'] as String,
        customerName: json['customer_name'] as String?,
        paymentMode: json['payment_mode'] as String?,
        saleAmount: (json['sale_amount'] as num?)?.toDouble(),
        saleAmountExcludingGst: (json['sale_amount_excluding_gst'] as num?)?.toDouble(),
        saleSource: json['sale_source'] as String,
        soldAt: json['sold_at'] as String,
        recordedByUserId: json['recorded_by_user_id'] as int?,
        recordedByDisplayName: json['recorded_by_display_name'] as String?,
        notes: json['notes'] as String?,
        tallyCompanyName: json['tally_company_name'] as String?,
        tallyVoucherNumber: json['tally_voucher_number'] as String?,
        printedInvoiceNumber: json['printed_invoice_number'] as String?,
        tallyVoucherType: json['tally_voucher_type'] as String?,
        createdAt: json['created_at'] as String,
      );

  @override
  List<Object?> get props => [id];
}

class SalesListFilters extends Equatable {
  const SalesListFilters({
    this.brandId,
    this.locationId,
    this.userId,
    this.invoiceNumber = '',
    this.customerName = '',
    this.paymentMode = '',
    this.saleSource = '',
    this.dateFrom = '',
    this.dateTo = '',
  });

  final int? brandId;
  final int? locationId;
  final int? userId;
  final String invoiceNumber;
  final String customerName;
  final String paymentMode;
  final String saleSource;
  final String dateFrom;
  final String dateTo;

  Map<String, dynamic> toQueryParams({
    required int page,
    required int pageSize,
    String? search,
    required SalesSortField sortField,
    required String sortDirection,
  }) {
    return {
      'page': page,
      'page_size': pageSize,
      'sort_field': sortField.apiName,
      'sort_direction': sortDirection,
      if (search != null && search.trim().isNotEmpty) 'search': search.trim(),
      if (brandId != null) 'brand_id': brandId,
      if (locationId != null) 'location_id': locationId,
      if (userId != null) 'user_id': userId,
      if (invoiceNumber.trim().isNotEmpty) 'invoice_number': invoiceNumber.trim(),
      if (customerName.trim().isNotEmpty) 'customer_name': customerName.trim(),
      if (paymentMode.trim().isNotEmpty) 'payment_mode': paymentMode.trim(),
      if (saleSource.isNotEmpty) 'sale_source': saleSource,
      if (dateFrom.isNotEmpty) 'date_from': '${dateFrom}T00:00:00Z',
      if (dateTo.isNotEmpty) 'date_to': '${dateTo}T23:59:59Z',
    };
  }

  SalesListFilters copyWith({
    int? brandId,
    int? locationId,
    int? userId,
    String? invoiceNumber,
    String? customerName,
    String? paymentMode,
    String? saleSource,
    String? dateFrom,
    String? dateTo,
    bool clearBrand = false,
    bool clearLocation = false,
    bool clearUser = false,
  }) {
    return SalesListFilters(
      brandId: clearBrand ? null : brandId ?? this.brandId,
      locationId: clearLocation ? null : locationId ?? this.locationId,
      userId: clearUser ? null : userId ?? this.userId,
      invoiceNumber: invoiceNumber ?? this.invoiceNumber,
      customerName: customerName ?? this.customerName,
      paymentMode: paymentMode ?? this.paymentMode,
      saleSource: saleSource ?? this.saleSource,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
    );
  }

  @override
  List<Object?> get props => [brandId, locationId, userId, invoiceNumber, customerName, paymentMode, saleSource, dateFrom, dateTo];
}

String formatSaleAmount(double? amount) {
  if (amount == null) return '—';
  return '₹${amount.round()}';
}

String saleSourceLabel(String source) => switch (source) {
      'manual' => 'Completed',
      'tally' => 'Synced',
      _ => source,
    };

const paymentModes = ['Cash', 'Card', 'UPI', 'Bank Transfer', 'Finance'];
