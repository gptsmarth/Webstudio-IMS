import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'bootstrap.dart';

Future<void> main() async {
  final container = await AppBootstrap.createContainer();
  runApp(
    UncontrolledProviderScope(
      container: container,
      child: const WebstudioImsApp(),
    ),
  );
}
