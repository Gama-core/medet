import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class User {
  final String name;
  final String email;
  final String password;

  User({required this.name, required this.email, required this.password});

  Map<String, dynamic> toJson() => {
    'name': name,
    'email': email,
    'password': password,
  };

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      name: json['name'],
      email: json['email'],
      password: json['password'],
    );
  }
}

class AuthService {
  static const String _userKey = 'registered_users';
  static const String _currentUserKey = 'current_user';

  // Inscription
  Future<bool> register(String name, String email, String password) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getStringList(_userKey) ?? [];
    
    // Vérifier si l'email existe déjà
    for (var uJson in usersJson) {
      final user = User.fromJson(jsonDecode(uJson));
      if (user.email == email) return false;
    }

    final newUser = User(name: name, email: email, password: password);
    usersJson.add(jsonEncode(newUser.toJson()));
    await prefs.setStringList(_userKey, usersJson);
    return true;
  }

  // Connexion
  Future<User?> login(String email, String password) async {
    final prefs = await SharedPreferences.getInstance();
    final usersJson = prefs.getStringList(_userKey) ?? [];

    for (var uJson in usersJson) {
      final user = User.fromJson(jsonDecode(uJson));
      if (user.email == email && user.password == password) {
        await prefs.setString(_currentUserKey, jsonEncode(user.toJson()));
        return user;
      }
    }
    return null;
  }

  // Déconnexion
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_currentUserKey);
  }

  // Vérifier si déjà connecté
  Future<User?> getCurrentUser() async {
    final prefs = await SharedPreferences.getInstance();
    final userJson = prefs.getString(_currentUserKey);
    if (userJson == null) return null;
    return User.fromJson(jsonDecode(userJson));
  }
}
