enum DefectSeverity { low, medium, high }

DefectSeverity _severityFromJson(String? raw) {
  switch (raw) {
    case 'high':
      return DefectSeverity.high;
    case 'medium':
      return DefectSeverity.medium;
    default:
      return DefectSeverity.low;
  }
}

class DefectInfo {
  const DefectInfo({
    required this.bbox,
    required this.type,
    required this.severity,
    required this.confidence,
    this.position3d,
  });

  final List<double> bbox;
  final String type;
  final DefectSeverity severity;
  final double confidence;
  final List<double>? position3d;

  factory DefectInfo.fromJson(Map<String, dynamic> json) => DefectInfo(
        bbox: (json['bbox'] as List).map((e) => (e as num).toDouble()).toList(),
        type: json['type'] as String,
        severity: _severityFromJson(json['severity'] as String?),
        confidence: (json['confidence'] as num).toDouble(),
        position3d: (json['position_3d'] as List?)
            ?.map((e) => (e as num).toDouble())
            .toList(),
      );
}

class DefectReport {
  const DefectReport({
    required this.totalDefectScore,
    required this.severityLevel,
    required this.defects,
  });

  final double totalDefectScore;
  final DefectSeverity severityLevel;
  final List<DefectInfo> defects;

  factory DefectReport.fromJson(Map<String, dynamic> json) => DefectReport(
        totalDefectScore: (json['total_defect_score'] as num).toDouble(),
        severityLevel: _severityFromJson(json['severity_level'] as String?),
        defects: (json['defects'] as List? ?? [])
            .cast<Map<String, dynamic>>()
            .map(DefectInfo.fromJson)
            .toList(),
      );
}
