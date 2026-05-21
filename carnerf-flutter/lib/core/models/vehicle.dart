enum Model3DStatus { none, processing, ready }

enum VehicleBodyType { sedan, suv, hatchback, coupe, wagon }

enum VehicleDriveType { twoWd, fourWd, awd }

Model3DStatus _model3DStatusFromJson(String? raw) {
  switch (raw) {
    case 'processing':
      return Model3DStatus.processing;
    case 'ready':
      return Model3DStatus.ready;
    default:
      return Model3DStatus.none;
  }
}

VehicleBodyType? _bodyTypeFromJson(String? raw) {
  switch (raw) {
    case 'sedan':
      return VehicleBodyType.sedan;
    case 'suv':
      return VehicleBodyType.suv;
    case 'hatchback':
      return VehicleBodyType.hatchback;
    case 'coupe':
      return VehicleBodyType.coupe;
    case 'wagon':
      return VehicleBodyType.wagon;
  }
  return null;
}

VehicleDriveType? _driveTypeFromJson(String? raw) {
  switch (raw) {
    case '2WD':
      return VehicleDriveType.twoWd;
    case '4WD':
      return VehicleDriveType.fourWd;
    case 'AWD':
      return VehicleDriveType.awd;
  }
  return null;
}

class Vehicle {
  const Vehicle({
    required this.id,
    required this.brand,
    required this.model,
    required this.year,
    this.trim,
    required this.fuelType,
    required this.transmission,
    required this.mileage,
    this.color,
    this.engineCc,
    this.region,
    this.thumbnailUrl,
    this.model3dUrl,
    required this.model3dStatus,
    this.options = const [],
    this.bodyType,
    this.driveType,
    this.seats,
    this.vinLast4,
    this.accidentCount,
    this.floodHistory,
    this.ownerChangeCount,
    this.firstRegisteredAt,
    this.inspectionDate,
    this.plateNumberMasked,
  });

  final int id;
  final String brand;
  final String model;
  final int year;
  final String? trim;
  final String fuelType;
  final String transmission;
  final int mileage;
  final String? color;
  final int? engineCc;
  final String? region;
  final String? thumbnailUrl;
  final String? model3dUrl;
  final Model3DStatus model3dStatus;
  final List<String> options;
  final VehicleBodyType? bodyType;
  final VehicleDriveType? driveType;
  final int? seats;
  final String? vinLast4;
  final int? accidentCount;
  final bool? floodHistory;
  final int? ownerChangeCount;
  final DateTime? firstRegisteredAt;
  final DateTime? inspectionDate;
  final String? plateNumberMasked;

  factory Vehicle.fromJson(Map<String, dynamic> json) => Vehicle(
        id: json['id'] as int,
        brand: json['brand'] as String,
        model: json['model'] as String,
        year: (json['year'] as num).toInt(),
        trim: json['trim'] as String?,
        fuelType: json['fuel_type'] as String,
        transmission: json['transmission'] as String,
        mileage: (json['mileage'] as num).toInt(),
        color: json['color'] as String?,
        engineCc: (json['engine_cc'] as num?)?.toInt(),
        region: json['region'] as String?,
        thumbnailUrl: json['thumbnail_url'] as String?,
        model3dUrl: json['model_3d_url'] as String?,
        model3dStatus: _model3DStatusFromJson(json['model_3d_status'] as String?),
        options: (json['options'] as List?)?.cast<String>() ?? const [],
        bodyType: _bodyTypeFromJson(json['body_type'] as String?),
        driveType: _driveTypeFromJson(json['drive_type'] as String?),
        seats: (json['seats'] as num?)?.toInt(),
        vinLast4: json['vin_last4'] as String?,
        accidentCount: (json['accident_count'] as num?)?.toInt(),
        floodHistory: json['flood_history'] as bool?,
        ownerChangeCount: (json['owner_change_count'] as num?)?.toInt(),
        firstRegisteredAt: _parseDate(json['first_registered_at']),
        inspectionDate: _parseDate(json['inspection_date']),
        plateNumberMasked: json['plate_number_masked'] as String?,
      );

  static DateTime? _parseDate(dynamic raw) {
    if (raw == null) return null;
    if (raw is String && raw.isEmpty) return null;
    return DateTime.tryParse(raw.toString());
  }

  String get displayTitle => '$year $brand $model${trim != null ? ' $trim' : ''}';
}
