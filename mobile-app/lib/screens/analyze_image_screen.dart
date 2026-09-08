import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/prediction.dart';
import '../services/api_service.dart';
import '../services/local_history_service.dart';
import '../theme/app_theme.dart';
import '../widgets/bounding_box_painter.dart';
import 'video_result_screen.dart';

class AnalyzeImageScreen extends StatefulWidget {
  final ApiService apiService;

  const AnalyzeImageScreen({super.key, required this.apiService});

  @override
  State<AnalyzeImageScreen> createState() => _AnalyzeImageScreenState();
}

class _AnalyzeImageScreenState extends State<AnalyzeImageScreen> {
  final ImagePicker _picker = ImagePicker();
  final LocalHistoryService _localHistory = LocalHistoryService();

  File? _imageFile;
  Uint8List? _imageBytes;
  ui.Image? _decodedImage;

  bool _loading = false;
  String? _loadingMessage;
  String? _error;
  PredictionResult? _result;
  double _confidenceThreshold = 0.5;

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        imageQuality: 90,
        maxWidth: 1920,
        maxHeight: 1080,
      );
      if (picked == null) return;

      final file = File(picked.path);
      final bytes = await file.readAsBytes();
      final decoded = await decodeImageFromList(bytes);

      setState(() {
        _imageFile = file;
        _imageBytes = bytes;
        _decodedImage = decoded;
        _result = null;
        _error = null;
        _loadingMessage = null;
      });
    } catch (e) {
      setState(() => _error = "Erreur lors de l'accès aux médias : $e");
    }
  }

  Future<void> _pickVideo(ImageSource source) async {
    try {
      final picked = await _picker.pickVideo(source: source);
      if (picked == null) return;

      final videoFile = File(picked.path);
      
      // On prépare l'appel API mais on n'attend pas ici !
      final analysisFuture = widget.apiService.predictVideo(videoFile);
      
      if (!mounted) return;

      // On navigue IMMÉDIATEMENT vers l'écran de résultats
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => VideoResultScreen(
            resultFuture: analysisFuture, 
            videoPath: videoFile.path,
          ),
        ),
      );
    } catch (e) {
      setState(() => _error = "Erreur lors de la sélection de la vidéo.");
    }
  }

  Future<void> _analyze() async {
    if (_imageFile == null) return;
    setState(() {
      _loading = true;
      _loadingMessage = 'Analyse de l\'image...';
      _error = null;
    });
    try {
      final result = await widget.apiService.predictImage(_imageFile!);
      setState(() => _result = result);
      
      // Enregistrement dans l'historique local
      await _localHistory.saveAnalysis(result, _imageFile!.path);

    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingMessage = null;
        });
      }
    }
  }

  void _reset() {
    setState(() {
      _imageFile = null;
      _imageBytes = null;
      _decodedImage = null;
      _result = null;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Analyser une image')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_imageBytes == null) _buildPickerPrompt() else _buildPreview(),
            const SizedBox(height: 16),
            _buildThresholdSlider(),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _imageFile == null || _loading ? null : _analyze,
                    icon: const Icon(Icons.search),
                    label:
                        Text(_loading ? 'Analyse en cours…' : 'Analyser l\'image'),
                  ),
                ),
                if (_imageFile != null) ...[
                  const SizedBox(width: 10),
                  OutlinedButton(onPressed: _reset, child: const Text('Réinitialiser')),
                ],
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              _ErrorBanner(message: _error!),
            ],
            if (_result != null) ...[
              const SizedBox(height: 20),
              if (_result!.isPolyp && _result!.yoloConfidence < _confidenceThreshold)
                _ResultCard(result: PredictionResult.notDetected(message: 'Sous le seuil de confiance'))
              else
                _ResultCard(result: _result!),
              if (_result!.allProbabilities != null && !(_result!.isPolyp && _result!.yoloConfidence < _confidenceThreshold)) ...[
                const SizedBox(height: 14),
                _ProbabilitiesCard(
                  probabilities: _result!.allProbabilities!,
                  detectedType: _result!.polypType,
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildThresholdSlider() {
    if (_loading) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.primaryBlue.withValues(alpha: 0.3)),
        ),
        child: Column(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              _loadingMessage ?? 'Analyse en cours...',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w500, color: AppColors.primaryBlue),
            ),
          ],
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE1E8ED)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Seuil de confiance',
                  style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.darkText)),
              Text('${(_confidenceThreshold * 100).round()}%',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, color: AppColors.primaryBlue)),
            ],
          ),
          Slider(
            value: _confidenceThreshold,
            min: 0.1,
            max: 0.95,
            divisions: 17,
            label: '${(_confidenceThreshold * 100).round()}%',
            onChanged: (value) {
              setState(() => _confidenceThreshold = value);
            },
          ),
          const Text(
            'Filtre les détections avec un score inférieur au seuil.',
            style: TextStyle(fontSize: 11, color: AppColors.mutedText),
          ),
        ],
      ),
    );
  }

  Widget _buildPickerPrompt() {
    return Container(
      height: 300,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDE4EA), width: 1.4),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.add_to_photos_outlined, size: 48, color: AppColors.mutedText),
          const SizedBox(height: 12),
          const Text('Importer un média à analyser',
              style: TextStyle(color: AppColors.darkText, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          const Text('Image ou Vidéo', style: TextStyle(color: AppColors.mutedText, fontSize: 13)),
          const SizedBox(height: 24),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: WrapAlignment.center,
            children: [
              _PickerButton(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: Icons.camera_alt_outlined,
                label: 'Photo',
              ),
              _PickerButton(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: Icons.photo_library_outlined,
                label: 'Galerie',
              ),
              _PickerButton(
                onPressed: () => _pickVideo(ImageSource.camera),
                icon: Icons.videocam_outlined,
                label: 'Filmer',
              ),
              _PickerButton(
                onPressed: () => _pickVideo(ImageSource.gallery),
                icon: Icons.video_library_outlined,
                label: 'Vidéo',
              ),
              _PickerButton(
                onPressed: _showStreamDialog,
                icon: Icons.podcasts_outlined,
                label: 'Flux Live',
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showStreamDialog() {
    final controller = TextEditingController(text: 'http://10.0.2.2:8000/predict/stream');
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Analyse de Flux Live'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Entrez l\'URL du flux RTSP ou HTTP :', style: TextStyle(fontSize: 13)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'rtsp://...',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Annuler')),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _startStreamAnalysis(controller.text);
            },
            child: const Text('Lancer'),
          ),
        ],
      ),
    );
  }

  Future<void> _startStreamAnalysis(String url) async {
    setState(() {
      _loading = true;
      _loadingMessage = 'Connexion au flux et analyse en cours...';
      _error = null;
    });

    try {
      final analysisFuture = widget.apiService.predictStream(url);
      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => VideoResultScreen(
            resultFuture: analysisFuture,
            videoPath: url,
          ),
        ),
      );
    } catch (e) {
      setState(() => _error = "Échec de l'analyse du flux : $e");
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _loadingMessage = null;
        });
      }
    }
  }

  Widget _buildPreview() {
    final naturalSize = Size(
      _decodedImage!.width.toDouble(),
      _decodedImage!.height.toDouble(),
    );
    final aspectRatio = naturalSize.width / naturalSize.height;

    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: AspectRatio(
        aspectRatio: aspectRatio,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.memory(_imageBytes!, fit: BoxFit.fill),
            if (_result?.boundingBox != null)
              CustomPaint(
                painter: BoundingBoxPainter(
                  box: _result!.boundingBox!,
                  naturalSize: naturalSize,
                  polypType: _result!.polypType,
                  label: _result!.polypLabel,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PickerButton extends StatelessWidget {
  final VoidCallback onPressed;
  final IconData icon;
  final String label;

  const _PickerButton({required this.onPressed, required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 24),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String message;
  const _ErrorBanner({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFBE9EC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFF3C0CB)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.danger, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: const TextStyle(color: AppColors.danger))),
        ],
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  final PredictionResult result;
  const _ResultCard({required this.result});

  @override
  Widget build(BuildContext context) {
    final color =
        result.isPolyp ? colorForPolypType(result.polypType) : AppColors.success;
    final icon =
        result.isPolyp ? Icons.warning_amber_rounded : Icons.check_circle_outline;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border(left: BorderSide(color: color, width: 5)),
        boxShadow: const [
          BoxShadow(color: Color(0x11142130), blurRadius: 8, offset: Offset(0, 2))
        ],
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 30),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  result.isPolyp ? result.polypLabel : 'Aucune anomalie détectée',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  'Score YOLO : ${(result.yoloConfidence * 100).round()}%'
                  '${result.confidence != null ? ' · Confiance type : ${(result.confidence! * 100).round()}%' : ''}',
                  style: const TextStyle(color: AppColors.mutedText, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProbabilitiesCard extends StatelessWidget {
  final Map<String, double> probabilities;
  final String? detectedType;

  const _ProbabilitiesCard(
      {required this.probabilities, required this.detectedType});

  @override
  Widget build(BuildContext context) {
    final entries = probabilities.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE1E8ED)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Probabilités par type (étage 2b)',
              style: TextStyle(fontWeight: FontWeight.w600, color: AppColors.darkText)),
          const SizedBox(height: 12),
          ...entries.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    SizedBox(width: 70, child: Text(e.key, style: const TextStyle(fontSize: 13))),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: e.value,
                          minHeight: 8,
                          backgroundColor: const Color(0xFFEEF2F5),
                          color: e.key == detectedType
                              ? AppColors.primaryBlue
                              : const Color(0xFFB9C6CE),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 42,
                      child: Text('${(e.value * 100).round()}%',
                          textAlign: TextAlign.right, style: const TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
