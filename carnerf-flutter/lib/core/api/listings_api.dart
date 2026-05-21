import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/listing.dart';
import 'api_client.dart';

enum ListingSort { newest, priceAsc, priceDesc, mileage, regionMatch }

String _sortToParam(ListingSort s) {
  switch (s) {
    case ListingSort.newest:
      return 'newest';
    case ListingSort.priceAsc:
      return 'price_asc';
    case ListingSort.priceDesc:
      return 'price_desc';
    case ListingSort.mileage:
      return 'mileage';
    case ListingSort.regionMatch:
      return 'region_match';
  }
}

class ListingQuery {
  const ListingQuery({
    this.brand,
    this.fuelType,
    this.region,
    this.priceMin,
    this.priceMax,
    this.yearMin,
    this.yearMax,
    this.search,
    this.sort,
    this.page,
    this.limit,
  });

  final String? brand;
  final String? fuelType;
  final String? region;
  final int? priceMin;
  final int? priceMax;
  final int? yearMin;
  final int? yearMax;
  final String? search;
  final ListingSort? sort;
  final int? page;
  final int? limit;

  Map<String, dynamic> toMap() => {
        if (brand != null) 'brand': brand,
        if (fuelType != null) 'fuel_type': fuelType,
        if (region != null) 'region': region,
        if (priceMin != null) 'price_min': priceMin,
        if (priceMax != null) 'price_max': priceMax,
        if (yearMin != null) 'year_min': yearMin,
        if (yearMax != null) 'year_max': yearMax,
        if (search != null) 'search': search,
        if (sort != null) 'sort': _sortToParam(sort!),
        if (page != null) 'page': page,
        if (limit != null) 'limit': limit,
      };
}

class ListingCount {
  const ListingCount({required this.count, required this.totalPages});
  final int count;
  final int totalPages;
}

class ListingsApi {
  ListingsApi(this._dio);
  final Dio _dio;

  Future<List<Listing>> list([ListingQuery query = const ListingQuery()]) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/listings/',
      queryParameters: query.toMap(),
    );
    return (r.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map(Listing.fromJson)
        .toList();
  }

  Future<ListingCount> count([ListingQuery query = const ListingQuery()]) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/listings/count/',
      queryParameters: query.toMap(),
    );
    return ListingCount(
      count: (r.data!['count'] as num).toInt(),
      totalPages: (r.data!['total_pages'] as num).toInt(),
    );
  }

  Future<Listing> get(int id) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/listings/$id/');
    return Listing.fromJson(r.data!);
  }

  Future<Listing> create(Map<String, dynamic> body) async {
    final r = await _dio.post<Map<String, dynamic>>('/api/listings/', data: body);
    return Listing.fromJson(r.data!);
  }
}

final listingsApiProvider =
    Provider<ListingsApi>((ref) => ListingsApi(ref.watch(apiClientProvider)));
