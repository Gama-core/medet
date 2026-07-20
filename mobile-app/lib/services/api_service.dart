import 'dart:convert';
import 'package:http/http.dart' as http;

import '../models/record.dart';

/// Client HTTP vers le backend FastAPI medet.
///
/// Change [baseUrl] pour pointer vers ton VPS une fois déployé
/// (ex: "https://medet.tondomaine.com").
class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = 'http://localhost:8000'});
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
}

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}
// ApiService({this.baseUrl = 'http://10.0.2.2:8000'});
