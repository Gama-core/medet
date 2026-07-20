import 'package:flutter/material.dart';

import '../models/record.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/record_card.dart';
import 'record_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _api = ApiService();

  late Future<List<RecordSummary>> _recordsFuture;

  @override
  void initState() {
    super.initState();
    _recordsFuture = _api.fetchRecentRecords();
  }

  Future<void> _refresh() async {
    setState(() {
      _recordsFuture = _api.fetchRecentRecords();
    });
    await _recordsFuture;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('medet — Examens récents'),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<RecordSummary>>(
          future: _recordsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return _ErrorState(
                  message: snapshot.error.toString(), onRetry: _refresh);
            }

            final records = snapshot.data ?? [];
            if (records.isEmpty) {
              return const _EmptyState();
            }

            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: records.length,
              itemBuilder: (context, index) {
                final record = records[index];
                return RecordCard(
                  record: record,
                  onTap: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RecordDetailScreen(
                            recordId: record.id, apiService: _api),
                      ),
                    );
                    _refresh();
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.inbox_outlined,
                size: 48, color: AppColors.mutedText),
            const SizedBox(height: 12),
            const Text(
              'Aucun examen enregistré pour le moment.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.mutedText),
            ),
          ],
        ),
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
      child: Padding(
        padding: const EdgeInsets.all(24),
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
      ),
    );
  }
}
