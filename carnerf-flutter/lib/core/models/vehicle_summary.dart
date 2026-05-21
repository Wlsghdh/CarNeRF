class VehicleSummary {
  const VehicleSummary({
    required this.summary,
    required this.pros,
    required this.cons,
    required this.knownIssues,
    this.reviewSummary,
  });

  final String summary;
  final List<String> pros;
  final List<String> cons;
  final List<String> knownIssues;
  final String? reviewSummary;

  factory VehicleSummary.fromJson(Map<String, dynamic> json) => VehicleSummary(
        summary: json['summary'] as String? ?? '',
        pros: (json['pros'] as List?)?.cast<String>() ?? const [],
        cons: (json['cons'] as List?)?.cast<String>() ?? const [],
        knownIssues:
            (json['known_issues'] as List?)?.cast<String>() ?? const [],
        reviewSummary: json['review_summary'] as String?,
      );
}
