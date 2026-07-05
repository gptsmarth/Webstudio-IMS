import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Professional scan overlay — dimmed mask, corner brackets, animated scan line.
class BarcodeViewfinderOverlay extends StatelessWidget {
  const BarcodeViewfinderOverlay({
    super.key,
    required this.scanRect,
    required this.scanLineProgress,
    this.hint,
  });

  final Rect scanRect;
  final double scanLineProgress;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Stack(
        fit: StackFit.expand,
        children: [
          CustomPaint(
            painter: _ViewfinderPainter(
              scanRect: scanRect,
              scanLineProgress: scanLineProgress,
            ),
          ),
          if (hint != null)
            Positioned(
              left: 16,
              right: 16,
              top: math.max(16, scanRect.top - 48),
              child: Text(
                hint!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  shadows: [Shadow(color: Colors.black54, blurRadius: 6)],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ViewfinderPainter extends CustomPainter {
  _ViewfinderPainter({
    required this.scanRect,
    required this.scanLineProgress,
  });

  final Rect scanRect;
  final double scanLineProgress;

  static const _cornerLength = 28.0;
  static const _cornerWidth = 4.0;
  static const _cornerRadius = 12.0;

  @override
  void paint(Canvas canvas, Size size) {
    final window = RRect.fromRectAndRadius(scanRect, const Radius.circular(_cornerRadius));

    final dimPaint = Paint()..color = const Color(0xB3000000);
    canvas.drawPath(
      Path.combine(
        PathOperation.difference,
        Path()..addRect(Offset.zero & size),
        Path()..addRRect(window),
      ),
      dimPaint,
    );

    final borderPaint = Paint()
      ..color = Colors.white70
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawRRect(window, borderPaint);

    final cornerPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = _cornerWidth
      ..strokeCap = StrokeCap.round;

    _drawCorners(canvas, scanRect, cornerPaint);

    final lineY = scanRect.top + (scanRect.height * scanLineProgress);
    final linePaint = Paint()
      ..shader = LinearGradient(
        colors: [
          Colors.red.withValues(alpha: 0),
          Colors.redAccent,
          Colors.red.withValues(alpha: 0),
        ],
        stops: const [0, 0.5, 1],
      ).createShader(Rect.fromLTWH(scanRect.left, lineY - 1, scanRect.width, 2))
      ..strokeWidth = 2;
    canvas.drawLine(
      Offset(scanRect.left + 8, lineY),
      Offset(scanRect.right - 8, lineY),
      linePaint,
    );
  }

  void _drawCorners(Canvas canvas, Rect rect, Paint paint) {
    final left = rect.left;
    final right = rect.right;
    final top = rect.top;
    final bottom = rect.bottom;

    canvas.drawLine(Offset(left, top + _cornerLength), Offset(left, top), paint);
    canvas.drawLine(Offset(left, top), Offset(left + _cornerLength, top), paint);

    canvas.drawLine(Offset(right - _cornerLength, top), Offset(right, top), paint);
    canvas.drawLine(Offset(right, top), Offset(right, top + _cornerLength), paint);

    canvas.drawLine(Offset(left, bottom - _cornerLength), Offset(left, bottom), paint);
    canvas.drawLine(Offset(left, bottom), Offset(left + _cornerLength, bottom), paint);

    canvas.drawLine(Offset(right - _cornerLength, bottom), Offset(right, bottom), paint);
    canvas.drawLine(Offset(right, bottom), Offset(right, bottom - _cornerLength), paint);
  }

  @override
  bool shouldRepaint(covariant _ViewfinderPainter oldDelegate) {
    return oldDelegate.scanRect != scanRect ||
        oldDelegate.scanLineProgress != scanLineProgress;
  }
}

/// Normalized scan window for [MobileScanner] — horizontal strip for one barcode row.
Rect barcodeScanWindow(Size viewport) {
  final width = viewport.width;
  final height = viewport.height;
  final windowWidth = width * 0.88;
  final windowHeight = math.min(height * 0.22, 140.0);
  return Rect.fromLTWH(
    (width - windowWidth) / 2,
    height * 0.34,
    windowWidth,
    windowHeight,
  );
}
