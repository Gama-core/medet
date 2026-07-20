import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const MedetApp());
}

class MedetApp extends StatelessWidget {
  const MedetApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'medet',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const HomeScreen(),
    );
  }
}
