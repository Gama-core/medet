import 'package:flutter/material.dart';

/// Palette partagée — cohérente avec le thème clair déjà mis en place côté
/// Streamlit (fond clair, bleu clair pour les actions, vert/orange/rouge pour
/// les statuts).
class AppColors {
  static const primaryBlue = Color(0xFF2E9BE8);
  static const lightBlue = Color(0xFFEAF4FC);
  static const darkText = Color(0xFF14213D);
  static const mutedText = Color(0xFF5C6B7A);
  static const background = Color(0xFFF7FAFC);
  static const success = Color(0xFF2E7D32);
  static const warning = Color(0xFFF9A825);
  static const danger = Color(0xFFC2185B);
}

ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primaryBlue,
      primary: AppColors.primaryBlue,
      surface: Colors.white,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: AppColors.darkText,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE1E8ED)),
      ),
      margin: const EdgeInsets.symmetric(vertical: 6),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryBlue,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
    ),
    textTheme: const TextTheme(
      titleLarge:
          TextStyle(color: AppColors.darkText, fontWeight: FontWeight.bold),
      titleMedium:
          TextStyle(color: AppColors.darkText, fontWeight: FontWeight.w600),
      bodyMedium: TextStyle(color: AppColors.darkText),
      bodySmall: TextStyle(color: AppColors.mutedText),
    ),
  );
}

/// Couleur associée à chaque type de polype (cohérent avec le pipeline backend).
Color colorForPolypType(String? type) {
  switch (type) {
    case '1p':
    case '1s':
      return AppColors.danger;
    case '2':
      return AppColors.warning;
    case '3':
      return const Color(0xFFB71C1C);
    default:
      return AppColors.mutedText;
  }
}
