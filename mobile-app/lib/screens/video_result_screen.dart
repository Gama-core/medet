import 'package:flutter/material.dart';
import '../models/prediction.dart';
import '../models/record.dart';
import '../theme/app_theme.dart';
import '../widgets/timeline_widget.dart';

class VideoResultScreen extends StatelessWidget {
  final VideoResult result;

  const VideoResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final duration = result.totalFramesRead / result.fpsSource;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Résultats Analyse Vidéo'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildStatsCard(),
            const SizedBox(height: 20),
            TimelineWidget(
              detections: result.detections,
              segments: result.segments,
              durationSeconds: duration,
            ),
            const SizedBox(height: 24),
            const Text(
              'Segments Détectés',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.darkText),
            ),
            const SizedBox(height: 12),
            if (result.segments.isEmpty)
              const _EmptyState()
            else
              ...result.segments.map((s) => _SegmentTile(segment: s)),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primaryBlue,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        children: [
          const Text(
            'Statistiques Globales',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _StatItem(label: 'Frames', value: '${result.framesAnalyzed}'),
              _StatItem(label: 'Durée', value: '${(result.totalFramesRead / result.fpsSource).toStringAsFixed(1)}s'),
              _StatItem(label: 'Segments', value: '${result.segments.length}'),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 12)),
      ],
    );
  }
}

class _SegmentTile extends StatelessWidget {
  final Segment segment;

  const _SegmentTile({required this.segment});

  @override
  Widget build(BuildContext context) {
    final color = colorForPolypType(segment.polypType);
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: const Color(0xFFE1E8ED)),
        boxShadow: const [BoxShadow(color: Color(0x0A000000), blurRadius: 4, offset: Offset(0, 2))],
      ),
      child: Row(
        children: [
          Container(
            width: 12,
            height: 50,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  segment.polypLabel,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                Text(
                  'De ${segment.startTimestampSeconds.toStringAsFixed(1)}s à ${segment.endTimestampSeconds.toStringAsFixed(1)}s',
                  style: const TextStyle(color: AppColors.mutedText, fontSize: 13),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${(segment.maxConfidence * 100).round()}%',
                style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 16),
              ),
              const Text('confiance max', style: TextStyle(fontSize: 10, color: AppColors.mutedText)),
            ],
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(30),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.grey.shade200, style: BorderStyle.solid),
      ),
      child: const Column(
        children: [
          Icon(Icons.check_circle_outline, color: AppColors.success, size: 40),
          SizedBox(height: 12),
          Text(
            'Aucune anomalie détectée dans cette vidéo.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.mutedText),
          ),
        ],
      ),
    );
  }
}
