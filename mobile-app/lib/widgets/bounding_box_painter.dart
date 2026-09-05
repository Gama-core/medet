import 'package:flutter/material.dart';

import '../models/prediction.dart';
import '../theme/app_theme.dart';

/// Dessine la bounding_box renvoyée par le backend sur l'image affichée.
/// Le widget parent doit contraindre la taille du Canvas pour qu'elle
/// corresponde exactement à l'image affichée (voir AnalyzeImageScreen :
/// AspectRatio calé sur les dimensions naturelles + BoxFit.fill), de sorte
/// que le simple ratio taille-affichée / taille-naturelle suffise à
/// repositionner la boîte correctement, quelle que soit la résolution
/// d'affichage.
class BoundingBoxPainter extends CustomPainter {
  final BoundingBox box;
  final Size naturalSize;
  final String? polypType;
  final String label;

  BoundingBoxPainter({
    required this.box,
    required this.naturalSize,
    required this.polypType,
    required this.label,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final scaleX = size.width / naturalSize.width;
    final scaleY = size.height / naturalSize.height;

    final rect = Rect.fromLTRB(
      box.x1 * scaleX,
      box.y1 * scaleY,
      box.x2 * scaleX,
      box.y2 * scaleY,
    );

    final color = colorForPolypType(polypType);
    final boxPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawRect(rect, boxPaint);

    final textPainter = TextPainter(
      text: TextSpan(
        text: label,
        style: const TextStyle(
            color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
      ),
      textDirection: TextDirection.ltr,
    )..layout();

    final labelTop = (rect.top - textPainter.height - 6).clamp(0.0, size.height);
    final labelRect = Rect.fromLTWH(
      rect.left,
      labelTop,
      textPainter.width + 10,
      textPainter.height + 4,
    );

    canvas.drawRect(labelRect, Paint()..color = color);
    textPainter.paint(canvas, Offset(labelRect.left + 5, labelRect.top + 2));
  }

  @override
  bool shouldRepaint(covariant BoundingBoxPainter oldDelegate) {
    return oldDelegate.box != box || oldDelegate.naturalSize != naturalSize;
  }
}
