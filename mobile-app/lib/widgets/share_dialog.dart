import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

import '../services/api_service.dart';

/// Boîte de dialogue pour partager un examen avec un confrère : génère un
/// lien via le backend, puis propose de le partager via les apps du système
/// (Messages, Mail, WhatsApp...) ou de le copier.
class ShareDialog extends StatefulWidget {
  final String recordId;
  final ApiService apiService;

  const ShareDialog(
      {super.key, required this.recordId, required this.apiService});

  @override
  State<ShareDialog> createState() => _ShareDialogState();
}

class _ShareDialogState extends State<ShareDialog> {
  String? _shareUrl;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _generateLink();
  }

  Future<void> _generateLink() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final url = await widget.apiService.shareRecord(widget.recordId);
      setState(() {
        _shareUrl = url;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Partager avec un confrère'),
      content: SizedBox(
        width: 320,
        child: _loading
            ? const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            : _error != null
                ? Text(_error!, style: const TextStyle(color: Colors.red))
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Ce lien donne accès uniquement à cet examen (anonyme, '
                        'sans identité patient). Toute personne disposant du '
                        'lien peut le consulter — à transmettre uniquement à '
                        'des confrères de confiance.',
                        style: TextStyle(fontSize: 13),
                      ),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF0F4F8),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: SelectableText(
                          _shareUrl ?? '',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ),
                    ],
                  ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Fermer'),
        ),
        if (_shareUrl != null)
          ElevatedButton.icon(
            onPressed: () {
              Share.share(_shareUrl!);
            },
            icon: const Icon(Icons.ios_share, size: 18),
            label: const Text('Partager'),
          ),
      ],
    );
  }
}
