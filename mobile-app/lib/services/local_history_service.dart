import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/prediction.dart';

class LocalHistoryItem {
  final DateTime date;
  final PredictionResult result;
  final String imagePath;

  LocalHistoryItem({required this.date, required this.result, required this.imagePath});

  Map<String, dynamic> toJson() => {
    'date': date.toIso8601String(),
    'result': _predictionToJson(result),
    'imagePath': imagePath,
  };

  factory LocalHistoryItem.fromJson(Map<String, dynamic> json) {
    return LocalHistoryItem(
      date: DateTime.parse(json['date']),
      result: PredictionResult.fromJson(json['result']),
      imagePath: json['imagePath'],
    );
  }

  static Map<String, dynamic> _predictionToJson(PredictionResult res) {
    return {
      'is_polyp': res.isPolyp,
      'polyp_type': res.polypType,
      'polyp_label': res.polypLabel,
      'confidence': res.confidence,
      'all_probabilities': res.allProbabilities,
      'yolo_confidence': res.yoloConfidence,
      'yolo_zone': res.yoloZone,
      'action': res.action,
      'processing_time_ms': res.processingTimeMs,
      // Le bounding box est plus complexe à sérialiser simplement ici, 
      // on peut l'omettre ou le gérer si besoin.
    };
  }
}

class LocalHistoryService {
  static const String _key = 'local_history';

  Future<void> saveAnalysis(PredictionResult result, String imagePath) async {
    final prefs = await SharedPreferences.getInstance();
    final history = await getHistory();
    
    final newItem = LocalHistoryItem(
      date: DateTime.now(),
      result: result,
      imagePath: imagePath,
    );
    
    history.insert(0, newItem);
    
    // On garde les 20 dernières analyses localement
    if (history.length > 20) {
      history.removeRange(20, history.length);
    }
    
    final String encoded = jsonEncode(history.map((e) => e.toJson()).toList());
    await prefs.setString(_key, encoded);
  }

  Future<List<LocalHistoryItem>> getHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final String? encoded = prefs.getString(_key);
    
    if (encoded == null) return [];
    
    final List<dynamic> decoded = jsonDecode(encoded);
    return decoded.map((e) => LocalHistoryItem.fromJson(e)).toList();
  }

  Future<void> clearHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
