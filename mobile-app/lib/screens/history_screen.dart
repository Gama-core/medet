import 'dart:io';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/record.dart';
import '../services/api_service.dart';
import '../services/local_history_service.dart';
import '../theme/app_theme.dart';
import '../widgets/record_card.dart';
import 'record_detail_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  final LocalHistoryService _localService = LocalHistoryService();
  
  late TabController _tabController;
  late Future<List<RecordSummary>> _remoteRecordsFuture;
  late Future<List<LocalHistoryItem>> _localRecordsFuture;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _remoteRecordsFuture = _api.fetchRecentRecords();
    _localRecordsFuture = _localService.getHistory();
  }

  Future<void> _refreshRemote() async {
    setState(() {
      _remoteRecordsFuture = _api.fetchRecentRecords();
    });
    await _remoteRecordsFuture;
  }

  Future<void> _refreshLocal() async {
    setState(() {
      _localRecordsFuture = _localService.getHistory();
    });
    await _localRecordsFuture;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.primaryBlue,
          labelColor: AppColors.primaryBlue,
          unselectedLabelColor: AppColors.mutedText,
          tabs: const [
            Tab(text: 'Serveur', icon: Icon(Icons.cloud_outlined)),
            Tab(text: 'Local', icon: Icon(Icons.phone_android_outlined)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildRemoteList(),
          _buildLocalList(),
        ],
      ),
    );
  }

  Widget _buildRemoteList() {
    return RefreshIndicator(
      onRefresh: _refreshRemote,
      child: FutureBuilder<List<RecordSummary>>(
        future: _remoteRecordsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _ErrorState(message: snapshot.error.toString(), onRetry: _refreshRemote);
          }
          final records = snapshot.data ?? [];
          if (records.isEmpty) return const _EmptyState(message: 'Aucun examen sur le serveur.');

          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: records.length,
            itemBuilder: (context, index) {
              final record = records[index];
              return RecordCard(
                record: record,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => RecordDetailScreen(recordId: record.id, apiService: _api),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Widget _buildLocalList() {
    return RefreshIndicator(
      onRefresh: _refreshLocal,
      child: FutureBuilder<List<LocalHistoryItem>>(
        future: _localRecordsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final records = snapshot.data ?? [];
          if (records.isEmpty) return const _EmptyState(message: 'Aucune analyse locale enregistrée.');

          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: records.length,
            itemBuilder: (context, index) {
              final item = records[index];
              return _LocalRecordCard(item: item);
            },
          );
        },
      ),
    );
  }
}

class _LocalRecordCard extends StatelessWidget {
  final LocalHistoryItem item;
  const _LocalRecordCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('dd/MM/yyyy — HH:mm');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(File(item.imagePath), width: 60, height: 60, fit: BoxFit.cover, 
                errorBuilder: (_, __, ___) => Container(width: 60, height: 60, color: Colors.grey.shade200, child: const Icon(Icons.image_not_supported)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.result.isPolyp ? item.result.polypLabel : 'Négatif',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  Text(dateFormat.format(item.date), style: const TextStyle(fontSize: 12, color: AppColors.mutedText)),
                  const SizedBox(height: 4),
                  Text('Score: ${(item.result.yoloConfidence * 100).round()}%', style: const TextStyle(fontSize: 12)),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: Colors.grey.shade400),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String message;
  const _EmptyState({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.history_outlined, size: 60, color: AppColors.mutedText),
          const SizedBox(height: 16),
          Text(message, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.mutedText)),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 48, color: AppColors.danger),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          ElevatedButton(onPressed: onRetry, child: const Text('Réessayer')),
        ],
      ),
    );
  }
}
