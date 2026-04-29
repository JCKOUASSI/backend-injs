import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persistance locale.
///
/// • Tokens JWT (access + refresh) → [FlutterSecureStorage] (Keystore Android /
///   Keychain iOS) : chiffrés au repos, inaccessibles sans déverrouillage de l'appareil.
/// • Données non sensibles (device_id, username, flags) → [SharedPreferences].
class StorageService {
  static const _kDeviceId = 'device_id';
  static const _kUsername = 'username';
  static const _kMustChangePassword = 'must_change_password';

  static const _kAccessToken = 'access_token';
  static const _kRefreshToken = 'refresh_token';

  static const _secure = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  // ── Tokens (stockage sécurisé) ──────────────────────────────────────────

  Future<String?> getAccessToken() => _secure.read(key: _kAccessToken);

  Future<String?> getRefreshToken() => _secure.read(key: _kRefreshToken);

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _secure.write(key: _kAccessToken, value: access);
    await _secure.write(key: _kRefreshToken, value: refresh);
  }

  Future<void> clearTokens() async {
    await _secure.delete(key: _kAccessToken);
    await _secure.delete(key: _kRefreshToken);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kMustChangePassword);
  }

  // ── Données non sensibles (SharedPreferences) ───────────────────────────

  Future<bool> getMustChangePassword() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kMustChangePassword) ?? false;
  }

  Future<void> setMustChangePassword(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kMustChangePassword, value);
  }

  Future<String> getOrCreateDeviceId() async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_kDeviceId);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final generated = 'MOBILE_${DateTime.now().millisecondsSinceEpoch}';
    await prefs.setString(_kDeviceId, generated);
    return generated;
  }

  Future<String?> getUsername() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kUsername);
  }

  Future<void> setUsername(String username) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUsername, username);
  }

}
