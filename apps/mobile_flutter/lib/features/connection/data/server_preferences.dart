import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../domain/server_models.dart';

const _savedServersKey = 'webstudio_saved_servers';
const _savedUsernameKey = 'saved_username';
const _rememberMeKey = 'remember_me';

class ServerPreferences {
  ServerPreferences(this._prefs);

  final SharedPreferences _prefs;

  List<SavedServer> listSavedServers() {
    final raw = _prefs.getString(_savedServersKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .whereType<Map<String, dynamic>>()
          .map(SavedServer.fromJson)
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> saveServer(SavedServer server) async {
    final existing = listSavedServers();
    final normalized = server.url.trim().replaceAll(RegExp(r'/+$'), '');
    final updated = [
      server.copyWith(
        url: normalized,
        lastConnectedAt: server.lastConnectedAt ?? DateTime.now(),
        lastSeenAt: DateTime.now(),
      ),
      ...existing.where((entry) => entry.url != normalized),
    ].take(8).toList();
    await _prefs.setString(
      _savedServersKey,
      jsonEncode(updated.map((e) => e.toJson()).toList()),
    );
  }

  Future<void> removeServer(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/+$'), '');
    final updated = listSavedServers().where((entry) => entry.url != normalized).toList();
    await _prefs.setString(
      _savedServersKey,
      jsonEncode(updated.map((e) => e.toJson()).toList()),
    );
  }

  String? getSavedUsername() => _prefs.getString(_savedUsernameKey);

  bool getRememberMe() => _prefs.getBool(_rememberMeKey) ?? false;

  Future<void> setRememberMe({required bool enabled, String? username}) async {
    await _prefs.setBool(_rememberMeKey, enabled);
    if (enabled && username != null && username.trim().isNotEmpty) {
      await _prefs.setString(_savedUsernameKey, username.trim());
    } else if (!enabled) {
      await _prefs.remove(_savedUsernameKey);
    }
  }
}
