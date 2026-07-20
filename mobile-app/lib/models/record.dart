/// Modèles de données correspondant aux schémas du backend (models/schemas.py).
///
/// Rappel confidentialité : aucun champ d'identité réelle du patient n'existe
/// ici — [referenceLabel] est un texte libre choisi par le médecin pour se
/// repérer (ex: "Salle 2 - matin"), jamais un nom ou un identifiant patient.
library;

class Segment {
  final double startTimestampSeconds;
  final double endTimestampSeconds;
  final double durationSeconds;
  final String? polypType;
  final String polypLabel;
  final double maxConfidence;
  final int frameCount;

  Segment({
    required this.startTimestampSeconds,
    required this.endTimestampSeconds,
    required this.durationSeconds,
    required this.polypType,
    required this.polypLabel,
    required this.maxConfidence,
    required this.frameCount,
  });

  factory Segment.fromJson(Map<String, dynamic> json) {
    return Segment(
      startTimestampSeconds:
          (json['start_timestamp_seconds'] as num).toDouble(),
      endTimestampSeconds: (json['end_timestamp_seconds'] as num).toDouble(),
      durationSeconds: (json['duration_seconds'] as num).toDouble(),
      polypType: json['polyp_type'] as String?,
      polypLabel: json['polyp_label'] as String,
      maxConfidence: (json['max_confidence'] as num).toDouble(),
      frameCount: json['frame_count'] as int,
    );
  }

  Map<String, dynamic> toJson() => {
        'start_timestamp_seconds': startTimestampSeconds,
        'end_timestamp_seconds': endTimestampSeconds,
        'duration_seconds': durationSeconds,
        'polyp_type': polypType,
        'polyp_label': polypLabel,
        'max_confidence': maxConfidence,
        'frame_count': frameCount,
      };
}

/// Vue allégée d'un enregistrement — utilisée dans la liste "examens récents".
class RecordSummary {
  final String id;
  final DateTime createdAt;
  final String sourceType;
  final String? referenceLabel;
  final int segmentCount;
  final List<String> typesDetected;
  final bool shareEnabled;

  RecordSummary({
    required this.id,
    required this.createdAt,
    required this.sourceType,
    required this.referenceLabel,
    required this.segmentCount,
    required this.typesDetected,
    required this.shareEnabled,
  });

  factory RecordSummary.fromJson(Map<String, dynamic> json) {
    return RecordSummary(
      id: json['id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      sourceType: json['source_type'] as String,
      referenceLabel: json['reference_label'] as String?,
      segmentCount: json['segment_count'] as int,
      typesDetected: List<String>.from(json['types_detected'] as List),
      shareEnabled: json['share_enabled'] as bool,
    );
  }
}

/// Vue complète d'un enregistrement — utilisée dans l'écran de détail.
class RecordDetail {
  final String id;
  final DateTime createdAt;
  final String sourceType;
  final String? referenceLabel;
  final String? notes;
  final List<Segment> segments;
  final Map<String, int> summary;
  final bool shareEnabled;
  final String? shareToken;

  RecordDetail({
    required this.id,
    required this.createdAt,
    required this.sourceType,
    required this.referenceLabel,
    required this.notes,
    required this.segments,
    required this.summary,
    required this.shareEnabled,
    required this.shareToken,
  });

  factory RecordDetail.fromJson(Map<String, dynamic> json) {
    return RecordDetail(
      id: json['id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      sourceType: json['source_type'] as String,
      referenceLabel: json['reference_label'] as String?,
      notes: json['notes'] as String?,
      segments: (json['segments'] as List)
          .map((s) => Segment.fromJson(s as Map<String, dynamic>))
          .toList(),
      summary: Map<String, int>.from(json['summary'] as Map),
      shareEnabled: json['share_enabled'] as bool,
      shareToken: json['share_token'] as String?,
    );
  }
}
