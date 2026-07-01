/// Coerce decoded JSON maps (often `Map<dynamic, dynamic>`) to `Map<String, dynamic>`.
Map<String, dynamic> asJsonMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  throw FormatException('Expected JSON object, got ${value.runtimeType}');
}

Map<String, dynamic>? asJsonMapOrNull(Object? value) {
  if (value == null) return null;
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return null;
}

List<Map<String, dynamic>> asJsonMapList(Object? value) {
  if (value is! List) return [];
  return value
      .map(asJsonMapOrNull)
      .whereType<Map<String, dynamic>>()
      .toList();
}
