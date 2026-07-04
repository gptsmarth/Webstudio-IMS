import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../data/barcode_scan_preferences.dart';
import '../domain/barcode_field_resolver.dart';

enum BarcodeScannerMode { single, continuous }

class BarcodeScannerScreen extends StatefulWidget {
  const BarcodeScannerScreen({
    super.key,
    this.mode = BarcodeScannerMode.single,
    this.onContinuousScan,
  });

  final BarcodeScannerMode mode;
  final void Function(BarcodeScanResult result)? onContinuousScan;

  @override
  State<BarcodeScannerScreen> createState() => _BarcodeScannerScreenState();
}

class _BarcodeScannerScreenState extends State<BarcodeScannerScreen> {
  bool _handled = false;
  bool _paused = false;
  bool _soundEnabled = true;
  bool _hapticEnabled = true;
  final _history = <BarcodeScanResult>[];
  final _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.normal,
    formats: const [
      BarcodeFormat.code128,
      BarcodeFormat.code39,
      BarcodeFormat.codabar,
      BarcodeFormat.ean13,
      BarcodeFormat.ean8,
      BarcodeFormat.upcA,
      BarcodeFormat.upcE,
      BarcodeFormat.itf,
      BarcodeFormat.dataMatrix,
    ],
  );

  bool get _continuous => widget.mode == BarcodeScannerMode.continuous;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    final sound = await BarcodeScanPreferences.soundEnabled();
    final haptic = await BarcodeScanPreferences.hapticEnabled();
    if (mounted) setState(() { _soundEnabled = sound; _hapticEnabled = haptic; });
  }

  Future<void> _toggleSound() async {
    final next = !_soundEnabled;
    await BarcodeScanPreferences.setSoundEnabled(next);
    if (mounted) setState(() => _soundEnabled = next);
  }

  Future<void> _toggleHaptic() async {
    final next = !_hapticEnabled;
    await BarcodeScanPreferences.setHapticEnabled(next);
    if (mounted) setState(() => _hapticEnabled = next);
  }

  void _feedback({required bool duplicate}) {
    if (_hapticEnabled) {
      HapticFeedback.heavyImpact();
    }
    if (_soundEnabled && !duplicate) {
      SystemSound.play(SystemSoundType.click);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_paused) return;
    if (!_continuous && _handled) return;
    final barcode = capture.barcodes.isNotEmpty ? capture.barcodes.first : null;
    final raw = barcode?.rawValue?.trim();
    if (raw == null || raw.isEmpty) return;

    final format = barcode?.format.name ?? 'unknown';
    final result = BarcodeFieldResolver.resolve(rawValue: raw, format: format);

    if (_continuous) {
      if (_history.any((entry) => entry.rawValue == result.rawValue)) {
        if (_hapticEnabled) HapticFeedback.heavyImpact();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Duplicate scan: ${result.rawValue}')),
        );
        return;
      }
      _feedback(duplicate: false);
      setState(() => _history.insert(0, result));
      widget.onContinuousScan?.call(result);
      return;
    }

    _handled = true;
    _feedback(duplicate: false);
    Navigator.of(context).pop(result);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_continuous ? 'Continuous scan' : 'Scan barcode'),
        actions: [
          if (_continuous)
            IconButton(
              icon: Icon(_paused ? Icons.play_arrow : Icons.pause),
              tooltip: _paused ? 'Resume' : 'Pause',
              onPressed: () => setState(() => _paused = !_paused),
            ),
          IconButton(
            icon: ValueListenableBuilder(
              valueListenable: _controller,
              builder: (context, state, child) {
                switch (state.torchState) {
                  case TorchState.on:
                    return const Icon(Icons.flash_on);
                  case TorchState.off:
                    return const Icon(Icons.flash_off);
                  case TorchState.auto:
                    return const Icon(Icons.flash_auto);
                  case TorchState.unavailable:
                    return const Icon(Icons.flash_off);
                }
              },
            ),
            onPressed: () => _controller.toggleTorch(),
          ),
          IconButton(
            icon: const Icon(Icons.cameraswitch_outlined),
            tooltip: 'Switch camera',
            onPressed: () => _controller.switchCamera(),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'sound') _toggleSound();
              if (value == 'haptic') _toggleHaptic();
            },
            itemBuilder: (context) => [
              CheckedPopupMenuItem(
                value: 'sound',
                checked: _soundEnabled,
                child: const Text('Scan sound'),
              ),
              CheckedPopupMenuItem(
                value: 'haptic',
                checked: _hapticEnabled,
                child: const Text('Haptic feedback'),
              ),
            ],
          ),
          if (_continuous)
            TextButton(
              onPressed: () => Navigator.of(context).pop(_history),
              child: const Text('Done'),
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                MobileScanner(
                  controller: _controller,
                  onDetect: _onDetect,
                  errorBuilder: (context, error) => Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.camera_alt_outlined, size: 48, color: Theme.of(context).colorScheme.error),
                          const SizedBox(height: 12),
                          Text(
                            'Camera unavailable',
                            style: Theme.of(context).textTheme.titleMedium,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            error.errorDetails?.message ??
                                'Allow camera access in Android Settings, then tap Retry.',
                            style: Theme.of(context).textTheme.bodySmall,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),
                          FilledButton.icon(
                            onPressed: () async {
                              await _controller.start();
                              if (mounted) setState(() {});
                            },
                            icon: const Icon(Icons.refresh),
                            label: const Text('Retry camera'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                if (_paused)
                  Container(
                    color: Colors.black54,
                    alignment: Alignment.center,
                    child: const Text('Paused', style: TextStyle(color: Colors.white, fontSize: 24)),
                  ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            padding: const EdgeInsets.all(12),
            child: Text(
              _continuous
                  ? 'Scanned ${_history.length} item(s). Manufacturer barcodes only — serial, model, and part number detected automatically.'
                  : 'Manufacturer barcodes: Code 128/39, Codabar, EAN, UPC, ITF, Data Matrix.',
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ),
          if (_continuous && _history.isNotEmpty)
            SizedBox(
              height: 120,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                itemCount: _history.length,
                itemBuilder: (context, index) {
                  final entry = _history[index];
                  return Card(
                    margin: const EdgeInsets.all(8),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(entry.targetField.label, style: Theme.of(context).textTheme.labelSmall),
                          Text(entry.rawValue, style: Theme.of(context).textTheme.titleSmall),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
