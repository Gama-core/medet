import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:mime/mime.dart';

import '../models/record.dart';
import '../models/prediction.dart';

/// Client HTTP vers le backend FastAPI medet.
///
/// Change [baseUrl] pour pointer vers ton VPS une fois déployé
/// (ex: "https://medet.tondomaine.com").
class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = 'http://10.0.2.2:8000'});
  // 10.0.2.2 = alias vers "localhost" de la machine hôte depuis l'émulateur Android.
  // Sur iOS simulator ou test physique, remplace par l'IP réelle du serveur.

  Future<List<RecordSummary>> fetchRecentRecords({int limit = 50}) async {
    final uri = Uri.parse('$baseUrl/records?limit=$limit');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw ApiException(
          'Impossible de charger les examens récents (${response.statusCode}).');
    }

    final List<dynamic> data = jsonDecode(response.body);
    return data.map((json) => RecordSummary.fromJson(json)).toList();
  }

  Future<RecordDetail> fetchRecord(String id) async {
    final uri = Uri.parse('$baseUrl/records/$id');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw ApiException('Examen introuvable (${response.statusCode}).');
    }

    return RecordDetail.fromJson(jsonDecode(response.body));
  }

  Future<void> deleteRecord(String id) async {
    final uri = Uri.parse('$baseUrl/records/$id');
    final response = await http.delete(uri);

    if (response.statusCode != 204) {
      throw ApiException('Suppression impossible (${response.statusCode}).');
    }
  }

  /// Active le partage et retourne l'URL complète à transmettre à un confrère.
  Future<String> shareRecord(String id) async {
    final uri = Uri.parse('$baseUrl/records/$id/share');
    final response = await http.post(uri);

    if (response.statusCode != 200) {
      throw ApiException('Partage impossible (${response.statusCode}).');
    }

    final data = jsonDecode(response.body);
    final path = data['share_url_path'] as String;
    return '$baseUrl$path';
  }

  Future<void> unshareRecord(String id) async {
    final uri = Uri.parse('$baseUrl/records/$id/share');
    final response = await http.delete(uri);

    if (response.statusCode != 204) {
      throw ApiException(
          'Désactivation du partage impossible (${response.statusCode}).');
    }
  }

  Future<RecordDetail> fetchSharedRecord(String token) async {
    final uri = Uri.parse('$baseUrl/shared/$token');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw ApiException(
          'Lien de partage invalide ou expiré (${response.statusCode}).');
    }

    return RecordDetail.fromJson(jsonDecode(response.body));
  }

  /// Envoie une image à /predict/image et retourne le résultat.
  ///
  /// ⚠️ Contrat confirmé : le backend renvoie un 404 (pas une erreur 4xx
  /// classique) quand aucun polype n'est détecté — on le traite comme un
  /// résultat "normal" (isPolyp = false), pas comme une exception.
  Future<PredictionResult> predictImage(File imageFile) async {
    final uri = Uri.parse('$baseUrl/predict/image');
    
    final mimeType = lookupMimeType(imageFile.path) ?? 'image/jpeg';

    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath(
        'file', 
        imageFile.path,
        contentType: MediaType.parse(mimeType),
      ));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    
    // Debug log pour voir ce que le serveur répond réellement
    print('Backend Response (${response.statusCode}): ${response.body}');

    if (response.statusCode == 404) {
      String? detail;
      try {
        final body = jsonDecode(response.body);
        detail = body['detail'] as String?;
      } catch (_) {}
      return PredictionResult.notDetected(message: detail);
    }

    if (response.statusCode != 200) {
      String errorMessage = 'Analyse impossible (${response.statusCode})';
      try {
        final body = jsonDecode(response.body);
        if (body['detail'] != null) {
          errorMessage = body['detail'].toString();
        }
      } catch (_) {}
      throw ApiException(errorMessage);
    }

    return PredictionResult.fromJson(jsonDecode(response.body));
  }

  /// Envoie une vidéo à /predict/video et retourne le résultat complet.
  Future<VideoResult> predictVideo(File videoFile, {int frameSkip = 5}) async {
    final uri = Uri.parse('$baseUrl/predict/video?frame_skip=$frameSkip');
    
    final mimeType = lookupMimeType(videoFile.path) ?? 'video/mp4';

    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath(
        'file', 
        videoFile.path,
        contentType: MediaType.parse(mimeType),
      ));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    
    print('Backend Video Response (${response.statusCode}): ${response.body}');

    if (response.statusCode != 200) {
      String errorMessage = 'Analyse vidéo impossible (${response.statusCode})';
      try {
        final body = jsonDecode(response.body);
        if (body['detail'] != null) {
          errorMessage = body['detail'].toString();
        }
      } catch (_) {}
      throw ApiException(errorMessage);
    }

    return VideoResult.fromJson(jsonDecode(response.body));
  }
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}
