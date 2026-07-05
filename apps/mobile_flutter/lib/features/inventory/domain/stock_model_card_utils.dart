import 'package:flutter/material.dart';

import 'inventory_models.dart';
import 'product_category.dart';

const int stockCardCollapsedSpecCount = 6;

const _descriptionPrefix = 'DESCRIPTION:\n';

class StockModelSpecLine {
  const StockModelSpecLine({required this.label, required this.value});

  final String label;
  final String value;
}

class SplitModelNotes {
  const SplitModelNotes({required this.description, required this.specNotes});

  final String description;
  final String specNotes;
}

SplitModelNotes splitModelNotes(String? notes) {
  if (notes == null || notes.trim().isEmpty) {
    return const SplitModelNotes(description: '', specNotes: '');
  }
  if (!notes.startsWith(_descriptionPrefix)) {
    return SplitModelNotes(description: '', specNotes: notes.trim());
  }

  final afterMarker = notes.substring(_descriptionPrefix.length);
  final lines = afterMarker.split('\n');
  final descriptionLines = <String>[];
  final specLines = <String>[];
  var inDescription = true;

  for (final line in lines) {
    final trimmed = line.trim();
    if (inDescription) {
      if (RegExp(r'^[A-Za-z][\w\s/&]*:\s+\S').hasMatch(trimmed)) {
        inDescription = false;
        specLines.add(line);
      } else {
        descriptionLines.add(line);
      }
    } else {
      specLines.add(line);
    }
  }

  return SplitModelNotes(
    description: descriptionLines.join('\n').trim(),
    specNotes: specLines.join('\n').trim(),
  );
}

List<StockModelSpecLine> parseNotesSpecLines(String? notes) {
  final specNotes = splitModelNotes(notes).specNotes;
  if (specNotes.trim().isEmpty) return [];

  final structured = specNotes.split('\n---\n').first.trim();
  final lines = <StockModelSpecLine>[];

  for (final rawLine in structured.split('\n')) {
    final line = rawLine.trim();
    if (line.isEmpty) continue;
    final colon = line.indexOf(':');
    if (colon <= 0) continue;
    final label = line.substring(0, colon).trim();
    final value = line.substring(colon + 1).trim();
    if (label.isNotEmpty && value.isNotEmpty) {
      lines.add(StockModelSpecLine(label: label, value: value));
    }
  }

  return lines;
}

String formatStorage(String value, String unit, String type) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) return 'Standard Storage';
  return '$trimmed $unit $type'.trim();
}

void _pushIfPresent(List<StockModelSpecLine> lines, String label, String? value) {
  final trimmed = value?.trim();
  if (trimmed != null && trimmed.isNotEmpty) {
    lines.add(StockModelSpecLine(label: label, value: trimmed));
  }
}

List<StockModelSpecLine> buildStockModelSpecLines(ProductModel model) {
  if (model.isAccessory) {
    final lines = <StockModelSpecLine>[
      StockModelSpecLine(label: 'Type', value: accessoryKindLabel(model.accessoryKind)),
    ];
    _pushIfPresent(lines, 'Part number', model.partNumber);
    _pushIfPresent(lines, 'Model number', model.modelNumber);
    _pushIfPresent(lines, 'Colors', model.colorOptions);
    lines.addAll(parseNotesSpecLines(model.notes));
    return lines;
  }

  final lines = <StockModelSpecLine>[
    StockModelSpecLine(label: 'Processor', value: model.cpu.trim().isEmpty ? 'Standard Processor' : model.cpu.trim()),
    StockModelSpecLine(
      label: 'Graphics',
      value: (model.gpu == null || model.gpu!.trim().isEmpty) ? 'Integrated Graphics' : model.gpu!.trim(),
    ),
    StockModelSpecLine(label: 'Memory', value: '${model.ramGb == 0 ? 16 : model.ramGb} GB RAM'),
    StockModelSpecLine(
      label: 'Storage',
      value: formatStorage(model.storageValue, model.storageUnit, model.storageType),
    ),
    StockModelSpecLine(
      label: 'Display',
      value: (model.display == null || model.display!.trim().isEmpty) ? '15.6" Standard Display' : model.display!.trim(),
    ),
  ];

  _pushIfPresent(lines, 'Colors', model.colorOptions);

  final noteLines = parseNotesSpecLines(model.notes);
  final seen = lines.map((line) => line.label.toLowerCase()).toSet();
  for (final line in noteLines) {
    final key = line.label.toLowerCase();
    if (!seen.contains(key)) {
      lines.add(line);
      seen.add(key);
    }
  }

  return lines;
}

const _retailerSpecOrder = [
  'type',
  'part number',
  'model number',
  'operating system',
  'os',
  'processor',
  'graphics',
  'memory',
  'memory type',
  'storage',
  'display',
  'colors',
  'battery',
  'weight',
  'connectivity',
  'keyboard',
  'webcam',
  'audio',
  'charger',
  'warranty',
];

List<StockModelSpecLine> orderStockCardSpecLines(List<StockModelSpecLine> lines) {
  final rank = <String, int>{
    for (var i = 0; i < _retailerSpecOrder.length; i++) _retailerSpecOrder[i]: i,
  };
  final sorted = [...lines];
  sorted.sort((left, right) {
    final leftRank = rank[left.label.toLowerCase()] ?? 99;
    final rightRank = rank[right.label.toLowerCase()] ?? 99;
    if (leftRank != rightRank) return leftRank.compareTo(rightRank);
    return left.label.compareTo(right.label);
  });
  return sorted;
}

String stockAvailabilityLabel(int availableUnits) {
  if (availableUnits <= 0) return 'Out of stock';
  return availableUnits == 1 ? '1 unit available' : '$availableUnits units available';
}

String? displayScreenHint(ProductModel model) {
  if (model.isAccessory) return null;
  return displayScreenHintFromText(model.display);
}

String? displayScreenHintFromText(String? display) {
  if (display == null || display.trim().isEmpty) return null;
  final text = display.trim();
  final inch = RegExp(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|")\b', caseSensitive: false).firstMatch(text);
  if (inch != null) return '${inch.group(1)}"';

  final cm = RegExp(r'(\d+(?:\.\d+)?)\s*cm\s*\((\d+(?:\.\d+)?)\)', caseSensitive: false).firstMatch(text);
  if (cm != null) return '${cm.group(1)}cm (${cm.group(2)})';

  final segment = text.split(RegExp(r'[,;]')).first.trim();
  if (segment.isNotEmpty && segment.length <= 28) return segment;
  return null;
}

String formatSpecBullet(StockModelSpecLine line) {
  final value = line.value.trim();
  final label = line.label.trim();
  if (label.isEmpty) return value;
  if (label.toLowerCase() == 'operating system') return value;
  if (value.toLowerCase().startsWith(label.toLowerCase())) return value;
  return '$label: $value';
}

String formatCardPrice(double? value) {
  if (value == null || value <= 0) return 'Price on request';
  return '₹ ${value.toStringAsFixed(2)}';
}

String? formatDetailPrice(double? value) {
  if (value == null || value <= 0) return null;
  return '₹ ${value.toStringAsFixed(2)}';
}

String modelDescriptionText(String? notes) {
  final split = splitModelNotes(notes);
  if (split.description.isNotEmpty) return split.description;
  return notes?.trim() ?? '';
}

String modelNumberLine(ProductModel model) {
  final modelNumber = model.modelNumber.trim();
  final partNumber = model.partNumber?.trim();
  if (model.isAccessory && partNumber != null && partNumber.isNotEmpty && partNumber != modelNumber) {
    return '$modelNumber · PN $partNumber';
  }
  return modelNumber;
}

IconData productCategoryPlaceholderIcon(ProductModel model) {
  return model.isAccessory ? Icons.mouse_outlined : Icons.laptop_mac_outlined;
}

/// Product title without repeating the brand line shown above it.
String displayModelTitle(String brandName, String modelName) {
  final brand = brandName.trim();
  final name = modelName.trim();
  if (name.isEmpty) return brand;
  if (brand.isEmpty) return name;
  if (name.toLowerCase().startsWith(brand.toLowerCase())) {
    final trimmed = name.substring(brand.length).trim();
    return trimmed.isEmpty ? name : trimmed;
  }
  return name;
}
