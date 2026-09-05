/// Modèle correspondant à PredictionResponse côté backend (models/schemas.py),
/// confirmé en conditions réelles via /predict/image.
import 'record.dart';

class BoundingBox {
  final int x1;
  final int y1;
  final int x2;
  final int y2;

  BoundingBox(
      {required this.x1, required this.y1, required this.x2, required this.y2});

  factory BoundingBox.fromJson(Map<String, dynamic> json) {
    return BoundingBox(
      x1: json['x1'] as int,
      y1: json['y1'] as int,
      x2: json['x2'] as int,
      y2: json['y2'] as int,
    );
  }
}

class PredictionResult {
  final bool isPolyp;
  final String? polypType;
  final String polypLabel;
  final double? confidence;
  final Map<String, double>? allProbabilities;
  final double yoloConfidence;
  final String yoloZone;
  final BoundingBox? boundingBox;
  final String action;
  final double processingTimeMs;

  PredictionResult({
    required this.isPolyp,
    required this.polypType,
    required this.polypLabel,
    required this.confidence,
    required this.allProbabilities,
    required this.yoloConfidence,
    required this.yoloZone,
    required this.boundingBox,
    required this.action,
    required this.processingTimeMs,
  });

  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    return PredictionResult(
      isPolyp: json['is_polyp'] as bool? ?? false,
      polypType: json['polyp_type'] as String?,
      polypLabel: json['polyp_label'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble(),
      allProbabilities: json['all_probabilities'] != null
          ? Map<String, double>.from(
              (json['all_probabilities'] as Map).map(
                (k, v) => MapEntry(k as String, (v as num).toDouble()),
              ),
            )
          : null,
      yoloConfidence: (json['yolo_confidence'] as num?)?.toDouble() ?? 0.0,
      yoloZone: json['yolo_zone'] as String? ?? '',
      boundingBox: json['bounding_box'] != null
          ? BoundingBox.fromJson(json['bounding_box'] as Map<String, dynamic>)
          : null,
      action: json['action'] as String? ?? '',
      processingTimeMs:
          (json['processing_time_ms'] as num?)?.toDouble() ?? 0.0,
    );
  }

  /// Le backend renvoie un 404 (et non une erreur) quand aucun polype n'est
  /// détecté au-dessus du seuil — ce constructeur transforme ce cas en un
  /// résultat "normal", exactement comme côté React.
  factory PredictionResult.notDetected({String? message}) {
    return PredictionResult(
      isPolyp: false,
      polypType: null,
      polypLabel: message ?? 'Aucune détection au-dessus du seuil.',
      confidence: null,
      allProbabilities: null,
      yoloConfidence: 0,
      yoloZone: '',
      boundingBox: null,
      action: 'no_detection',
      processingTimeMs: 0,
    );
  }
}

class FrameResult {
  final int frameIndex;
  final double timestampSeconds;
  final PredictionResult? prediction;

  FrameResult({
    required this.frameIndex,
    required this.timestampSeconds,
    this.prediction,
  });

  factory FrameResult.fromJson(Map<String, dynamic> json) {
    return FrameResult(
      frameIndex: json['frame_index'] as int,
      timestampSeconds: (json['timestamp_seconds'] as num).toDouble(),
      prediction: json['prediction'] != null
          ? PredictionResult.fromJson(json['prediction'] as Map<String, dynamic>)
          : null,
    );
  }
}

class VideoResult {
  final int totalFramesRead;
  final int framesAnalyzed;
  final double fpsSource;
  final List<FrameResult> detections;
  final List<Segment> segments;
  final double processingTimeMs;

  VideoResult({
    required this.totalFramesRead,
    required this.framesAnalyzed,
    required this.fpsSource,
    required this.detections,
    required this.segments,
    required this.processingTimeMs,
  });

  factory VideoResult.fromJson(Map<String, dynamic> json) {
    return VideoResult(
      totalFramesRead: json['total_frames_read'] as int,
      framesAnalyzed: json['frames_analyzed'] as int,
      fpsSource: (json['fps_source'] as num).toDouble(),
      detections: (json['detections'] as List)
          .map((d) => FrameResult.fromJson(d as Map<String, dynamic>))
          .toList(),
      segments: (json['segments'] as List)
          .map((s) => Segment.fromJson(s as Map<String, dynamic>))
          .toList(),
      processingTimeMs: (json['processing_time_ms'] as num).toDouble(),
    );
  }
}
