import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../models/prediction.dart';
import '../models/record.dart';
import '../theme/app_theme.dart';

class TimelineWidget extends StatelessWidget {
  final List<FrameResult> detections;
  final List<Segment> segments;
  final double durationSeconds;

  const TimelineWidget({
    super.key,
    required this.detections,
    required this.segments,
    required this.durationSeconds,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 260,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE1E8ED)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Chronologie de l\'examen',
            style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.darkText),
          ),
          const SizedBox(height: 4),
          const Text(
            'Évolution de la confiance au cours du temps',
            style: TextStyle(fontSize: 11, color: AppColors.mutedText),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: ScatterChart(
              ScatterChartData(
                scatterSpots: _getSpots(),
                minX: 0,
                maxX: durationSeconds,
                minY: 0,
                maxY: 1.0,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: true,
                  getDrawingHorizontalLine: (value) => const FlLine(color: Color(0xFFE7EDF1), strokeWidth: 1),
                  getDrawingVerticalLine: (value) => const FlLine(color: Color(0xFFE7EDF1), strokeWidth: 1),
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, meta) => Text(
                        '${(value * 100).toInt()}%',
                        style: const TextStyle(fontSize: 10, color: AppColors.mutedText),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      getTitlesWidget: (value, meta) => Text(
                        '${value.toInt()}s',
                        style: const TextStyle(fontSize: 10, color: AppColors.mutedText),
                      ),
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                scatterTouchData: ScatterTouchData(
                  enabled: true,
                  handleBuiltInTouches: true,
                  touchTooltipData: ScatterTouchTooltipData(
                    getTooltipColor: (spot) => Colors.white.withValues(alpha: 0.9),
                    getTooltipItems: (ScatterSpot touchedSpot) {
                      final index = detections.indexWhere((d) => 
                        d.timestampSeconds == touchedSpot.x && 
                        (d.prediction?.yoloConfidence ?? 0.0) == touchedSpot.y
                      );
                      
                      if (index == -1) return null;
                      
                      final detection = detections[index];
                      final isPolyp = detection.prediction?.isPolyp ?? false;
                      return ScatterTooltipItem(
                        't = ${touchedSpot.x.toStringAsFixed(1)}s\n',
                        textStyle: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.darkText),
                        children: [
                          TextSpan(
                            text: isPolyp ? '${detection.prediction!.polypLabel}\n' : 'Normal\n',
                            style: TextStyle(color: isPolyp ? colorForPolypType(detection.prediction!.polypType) : AppColors.success),
                          ),
                          TextSpan(
                            text: 'Confiance : ${(touchedSpot.y * 100).round()}%',
                            style: const TextStyle(color: AppColors.mutedText, fontWeight: FontWeight.normal),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<ScatterSpot> _getSpots() {
    return detections.map((d) {
      final conf = d.prediction?.yoloConfidence ?? 0.0;
      final isPolyp = d.prediction?.isPolyp ?? false;
      
      return ScatterSpot(
        d.timestampSeconds,
        conf,
        dotPainter: FlDotCirclePainter(
          radius: isPolyp ? 5.0 : 3.0,
          color: isPolyp ? colorForPolypType(d.prediction?.polypType) : const Color(0xFFB9C6CE),
          strokeWidth: 0,
        ),
      );
    }).toList();
  }
}
