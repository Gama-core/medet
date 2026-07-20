import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/record.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/share_dialog.dart';

class RecordDetailScreen extends StatefulWidget {
  final String recordId;
  final ApiService apiService;

  const RecordDetailScreen(
      {super.key, required this.recordId, required this.apiService});

  @override
  State<RecordDetailScreen> createState() => _RecordDetailScreenState();
}

class _RecordDetailScreenState extends State<RecordDetailScreen> {
  late Future<RecordDetail> _recordFuture;

  @override
  void initState() {
    super.initState();
    _recordFuture = widget.apiService.fetchRecord(widget.recordId);
  }

  Future<void> _openShareDialog() async {
    await showDialog(
      context: context,
      builder: (_) =>
          ShareDialog(recordId: widget.recordId, apiService: widget.apiService),
    );
    setState(() {
      _recordFuture = widget.apiService.fetchRecord(widget.recordId);
    });
  }

  Future<void> _confirmDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Supprimer cet examen ?'),
        content: const Text('Cette action est définitive.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Annuler')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Supprimer',
                style: TextStyle(color: AppColors.danger)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await widget.apiService.deleteRecord(widget.recordId);
      if (mounted) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Détail de l\'examen'),
        actions: [
          IconButton(
              icon: const Icon(Icons.share), onPressed: _openShareDialog),
          IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: _confirmDelete),
        ],
      ),
      body: FutureBuilder<RecordDetail>(
        future: _recordFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text(snapshot.error.toString()));
          }

          final record = snapshot.data!;
          final dateFormat = DateFormat('dd/MM/yyyy — HH:mm');

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                record.referenceLabel ?? 'Examen sans libellé',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 4),
              Text(dateFormat.format(record.createdAt),
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              Text('Source : ${record.sourceType}',
                  style: Theme.of(context).textTheme.bodySmall),
              if (record.shareEnabled) ...[
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.lightBlue,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.share, size: 14, color: AppColors.primaryBlue),
                      SizedBox(width: 6),
                      Text('Partagé avec un confrère',
                          style: TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 20),
              Text('Segments détectés (${record.segments.length})',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              if (record.segments.isEmpty)
                const Text('Aucune anomalie détectée.',
                    style: TextStyle(color: AppColors.mutedText)),
              ...record.segments.map((seg) => _SegmentTile(segment: seg)),
              if (record.notes != null && record.notes!.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text('Notes', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(record.notes!),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _SegmentTile extends StatelessWidget {
  final Segment segment;
  const _SegmentTile({required this.segment});

  String _formatTime(double seconds) {
    final duration = Duration(milliseconds: (seconds * 1000).round());
    final m = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final color = colorForPolypType(segment.polypType);

    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withValues(alpha: 0.15),
          child: Text(
            segment.polypType ?? '?',
            style: TextStyle(
                color: color, fontWeight: FontWeight.bold, fontSize: 12),
          ),
        ),
        title: Text(segment.polypLabel),
        subtitle: Text(
          '${_formatTime(segment.startTimestampSeconds)} → '
          '${_formatTime(segment.endTimestampSeconds)}  '
          '(${segment.durationSeconds.toStringAsFixed(1)}s, ${segment.frameCount} frames)',
        ),
        trailing: Text(
          '${(segment.maxConfidence * 100).toStringAsFixed(0)}%',
          style: TextStyle(color: color, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}
