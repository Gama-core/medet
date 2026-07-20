import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/record.dart';
import '../theme/app_theme.dart';

class RecordCard extends StatelessWidget {
  final RecordSummary record;
  final VoidCallback onTap;

  const RecordCard({super.key, required this.record, required this.onTap});

  IconData _iconForSource(String sourceType) {
    switch (sourceType) {
      case 'image':
        return Icons.image_outlined;
      case 'video':
        return Icons.videocam_outlined;
      case 'webcam':
        return Icons.camera_alt_outlined;
      case 'stream':
        return Icons.podcasts_outlined;
      default:
        return Icons.description_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('dd/MM/yyyy — HH:mm');

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: AppColors.lightBlue,
                child: Icon(_iconForSource(record.sourceType),
                    color: AppColors.primaryBlue),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      record.referenceLabel ?? 'Examen sans libellé',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      dateFormat.format(record.createdAt),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      children: record.typesDetected
                          .map(
                            (type) => Chip(
                              label: Text(type,
                                  style: const TextStyle(
                                      fontSize: 12, color: Colors.white)),
                              backgroundColor: colorForPolypType(type),
                              padding: EdgeInsets.zero,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              visualDensity: VisualDensity.compact,
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
              if (record.shareEnabled)
                const Padding(
                  padding: EdgeInsets.only(left: 4),
                  child:
                      Icon(Icons.share, size: 18, color: AppColors.mutedText),
                ),
              const Icon(Icons.chevron_right, color: AppColors.mutedText),
            ],
          ),
        ),
      ),
    );
  }
}
