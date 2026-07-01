import 'package:equatable/equatable.dart';

class GlobalSearchHit extends Equatable {
  const GlobalSearchHit({
    required this.type,
    required this.id,
    required this.title,
    required this.subtitle,
    this.routeHint,
  });

  final String type;
  final String id;
  final String title;
  final String subtitle;
  final String? routeHint;

  factory GlobalSearchHit.fromJson(Map<String, dynamic> json) => GlobalSearchHit(
        type: json['type'] as String? ?? 'unknown',
        id: json['id']?.toString() ?? '',
        title: json['title'] as String? ?? json['label'] as String? ?? '',
        subtitle: json['subtitle'] as String? ?? json['description'] as String? ?? '',
        routeHint: json['route_hint'] as String?,
      );

  @override
  List<Object?> get props => [type, id];
}

class GlobalSearchResult extends Equatable {
  const GlobalSearchResult({required this.query, required this.hits});

  final String query;
  final List<GlobalSearchHit> hits;

  factory GlobalSearchResult.fromJson(Map<String, dynamic> json) {
    final rawHits = json['results'] ?? json['hits'] ?? json['items'];
    final hits = rawHits is List
        ? rawHits.whereType<Map<String, dynamic>>().map(GlobalSearchHit.fromJson).toList()
        : <GlobalSearchHit>[];
    return GlobalSearchResult(
      query: json['query'] as String? ?? '',
      hits: hits,
    );
  }

  @override
  List<Object?> get props => [query, hits];
}
