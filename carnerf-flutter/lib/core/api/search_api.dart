import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/listing.dart';
import 'api_client.dart';

class CompareResult {
  const CompareResult({required this.items, required this.tags});
  final List<Listing> items;
  final Map<String, int> tags;
}

class AiRecommendResult {
  const AiRecommendResult({
    required this.parsedFilters,
    required this.listings,
    required this.relaxLevel,
  });

  final Map<String, dynamic> parsedFilters;
  final List<ListingWithScore> listings;
  final int relaxLevel;
}

class ListingWithScore {
  const ListingWithScore({required this.listing, required this.matchScore});
  final Listing listing;
  final double matchScore;
}

class PopularKeyword {
  const PopularKeyword({required this.text, required this.count});
  final String text;
  final int count;

  factory PopularKeyword.fromJson(Map<String, dynamic> json) => PopularKeyword(
        text: json['text'] as String,
        count: (json['count'] as num).toInt(),
      );
}

class SearchApi {
  SearchApi(this._dio);
  final Dio _dio;

  Future<List<String>> autocomplete(String q, {int limit = 8}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/search/autocomplete/',
      queryParameters: {'q': q, 'limit': limit},
    );
    return (r.data!['suggestions'] as List).cast<String>();
  }

  Future<CompareResult> compare(List<int> ids) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/search/compare/',
      queryParameters: {'ids': ids.join(',')},
    );
    final items = (r.data!['items'] as List)
        .cast<Map<String, dynamic>>()
        .map(Listing.fromJson)
        .toList();
    final tags = (r.data!['tags'] as Map).map(
      (k, v) => MapEntry(k.toString(), (v as num).toInt()),
    );
    return CompareResult(items: items, tags: tags);
  }

  Future<AiRecommendResult> aiRecommend(String query) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/search/ai-recommend/',
      data: {'query': query},
    );
    final listings = (r.data!['listings'] as List).cast<Map<String, dynamic>>().map(
      (m) {
        final score = (m['match_score'] as num).toDouble();
        return ListingWithScore(listing: Listing.fromJson(m), matchScore: score);
      },
    ).toList();
    return AiRecommendResult(
      parsedFilters: (r.data!['parsed_filters'] as Map?)?.cast<String, dynamic>() ?? const {},
      listings: listings,
      relaxLevel: (r.data!['relax_level'] as num).toInt(),
    );
  }

  Future<List<PopularKeyword>> popularKeywords() async {
    final r = await _dio.get<Map<String, dynamic>>('/api/search/popular-keywords/');
    return (r.data!['keywords'] as List)
        .cast<Map<String, dynamic>>()
        .map(PopularKeyword.fromJson)
        .toList();
  }
}

final searchApiProvider =
    Provider<SearchApi>((ref) => SearchApi(ref.watch(apiClientProvider)));
