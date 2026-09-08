import 'dart:io';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../models/prediction.dart';
import '../models/record.dart';
import '../theme/app_theme.dart';
import '../widgets/timeline_widget.dart';

class VideoResultScreen extends StatefulWidget {
  final Future<VideoResult> resultFuture;
  final String videoPath;

  const VideoResultScreen({super.key, required this.resultFuture, required this.videoPath});

  @override
  State<VideoResultScreen> createState() => _VideoResultScreenState();
}

class _VideoResultScreenState extends State<VideoResultScreen> {
  late VideoPlayerController _controller;
  bool _isVideoInitialized = false;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
  }

  Future<void> _initializeVideo() async {
    if (widget.videoPath.startsWith('http')) {
      _controller = VideoPlayerController.networkUrl(Uri.parse(widget.videoPath));
    } else {
      _controller = VideoPlayerController.file(File(widget.videoPath));
    }

    try {
      await _controller.initialize();
      setState(() {
        _isVideoInitialized = true;
      });
      _controller.play();
      _controller.setLooping(true);
    } catch (e) {
      debugPrint("Erreur initialisation vidéo: $e");
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analyse Vidéo'),
      ),
      body: Column(
        children: [
          // 1. LE LECTEUR VIDÉO (Toujours présent en haut)
          _buildVideoPlayer(),

          // 2. LE CONTENU (Scrollable)
          Expanded(
            child: FutureBuilder<VideoResult>(
              future: widget.resultFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return _buildAnalyzingState();
                }

                if (snapshot.hasError) {
                  return _buildErrorState(snapshot.error.toString());
                }

                final result = snapshot.data!;
                final duration = result.totalFramesRead / result.fpsSource;

                return SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _buildStatsCard(result),
                      const SizedBox(height: 20),
                      TimelineWidget(
                        detections: result.detections,
                        segments: result.segments,
                        durationSeconds: duration,
                      ),
                      const SizedBox(height: 24),
                      const Text(
                        'Détections par Type',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.darkText),
                      ),
                      const SizedBox(height: 12),
                      if (result.segments.isEmpty)
                        const _EmptyState()
                      else
                        _buildGroupedSegments(result.segments),
                      const SizedBox(height: 30),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVideoPlayer() {
    return Container(
      width: double.infinity,
      height: 220,
      color: Colors.black,
      child: _isVideoInitialized
          ? Stack(
              alignment: Alignment.bottomCenter,
              children: [
                AspectRatio(
                  aspectRatio: _controller.value.aspectRatio,
                  child: VideoPlayer(_controller),
                ),
                VideoProgressIndicator(_controller, allowScrubbing: true),
                Positioned(
                  top: 10,
                  right: 10,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red.withValues(alpha: 0.8),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.circle, color: Colors.white, size: 10),
                        SizedBox(width: 4),
                        Text('LIVE', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                ),
              ],
            )
          : const Center(child: CircularProgressIndicator(color: Colors.white)),
    );
  }

  Widget _buildAnalyzingState() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const LinearProgressIndicator(),
          const SizedBox(height: 20),
          const Text(
            'Analyse IA en cours...',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.darkText),
          ),
          const SizedBox(height: 8),
          const Text(
            'L\'IA détecte et groupe les polypes par type. Les résultats apparaîtront dès la fin du traitement.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.mutedText, fontSize: 13),
          ),
          const SizedBox(height: 30),
          // Squelette pour l'aspect "React"
          _buildSkeletonCard('Type 1s (Sessile)', 'Analyse en cours...'),
          _buildSkeletonCard('Type 2 (Plan)', 'En attente...'),
        ],
      ),
    );
  }

  Widget _buildSkeletonCard(String title, String status) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: Colors.grey.shade50,
      child: ListTile(
        leading: CircleAvatar(backgroundColor: Colors.grey.shade200, child: const Icon(Icons.search, color: Colors.grey)),
        title: Text(title, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
        subtitle: Text(status, style: const TextStyle(color: Colors.grey, fontSize: 11)),
      ),
    );
  }

  Widget _buildErrorState(String error) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 60, color: AppColors.danger),
            const SizedBox(height: 16),
            const Text('Échec de l\'analyse', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(error, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.mutedText)),
          ],
        ),
      ),
    );
  }

  Widget _buildGroupedSegments(List<Segment> segments) {
    final groups = <String, List<Segment>>{};
    for (var s in segments) {
      groups.putIfAbsent(s.polypLabel, () => []).add(s);
    }

    return Column(
      children: groups.entries.map((entry) {
        final label = entry.key;
        final instances = entry.value;
        final type = instances.first.polypType;
        final color = colorForPolypType(type);

        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(15),
            side: BorderSide(color: color.withValues(alpha: 0.3)),
          ),
          child: ExpansionTile(
            leading: CircleAvatar(
              backgroundColor: color.withValues(alpha: 0.1),
              child: Text('${instances.length}', 
                style: TextStyle(color: color, fontWeight: FontWeight.bold)),
            ),
            title: Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text('${instances.length} occurrence(s) détectée(s)'),
            children: instances.map((s) => _SegmentInstanceTile(segment: s)).toList(),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildStatsCard(VideoResult result) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primaryBlue,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        children: [
          const Text(
            'Bilan de l\'analyse',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _StatItem(label: 'Images', value: '${result.framesAnalyzed}'),
              _StatItem(label: 'Durée', value: '${(result.totalFramesRead / result.fpsSource).toStringAsFixed(1)}s'),
              _StatItem(label: 'Anomalies', value: '${result.segments.length}'),
            ],
          ),
        ],
      ),
    );
  }
}

class _SegmentInstanceTile extends StatelessWidget {
  final Segment segment;
  const _SegmentInstanceTile({required this.segment});

  @override
  Widget build(BuildContext context) {
    final color = colorForPolypType(segment.polypType);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Color(0xFFEEEEEE))),
      ),
      child: Row(
        children: [
          Icon(Icons.timer_outlined, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${segment.startTimestampSeconds.toStringAsFixed(1)}s → ${segment.endTimestampSeconds.toStringAsFixed(1)}s',
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                ),
                Text(
                  'Durée: ${segment.durationSeconds.toStringAsFixed(1)}s · Confiance: ${(segment.maxConfidence * 100).round()}%',
                  style: const TextStyle(color: AppColors.mutedText, fontSize: 11),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, size: 16, color: AppColors.mutedText),
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

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(30),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: const Column(
        children: [
          Icon(Icons.check_circle_outline, color: AppColors.success, size: 40),
          SizedBox(height: 12),
          Text('Aucune anomalie détectée.', textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
