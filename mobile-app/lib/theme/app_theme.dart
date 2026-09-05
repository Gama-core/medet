import 'package:flutter/material.dart';

/// Palette partagée — cohérente avec le thème clair déjà mis en place côté
/// Streamlit (fond clair, bleu clair pour les actions, vert/orange/rouge pour
/// les statuts).
class AppColors {
  static const primaryBlue = Color(0xFF00B4D8); // Turquoise vif
  static const accentTurquoise = Color(0xFF48CAE4);
  static const lightBlue = Color(0xFFCAF0F8);
  static const darkText = Color(0xFF03045E);
  static const mutedText = Color(0xFF0077B6);
  static const background = Color(0xFFF0F9FF);
  static const success = Color(0xFF2D6A4F);
  static const warning = Color(0xFFF9A825);
  static const danger = Color(0xFFC9184A);
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
