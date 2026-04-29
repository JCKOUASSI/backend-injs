import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Lecture centralisée des variables (assets/app.env + éventuels --dart-define).
class AppEnv {
  AppEnv._();

  static const String _apiFromDefine = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );
  static const String _logoutFromDefine = String.fromEnvironment(
    'SUPERVISOR_LOGOUT_CODE',
    defaultValue: '',
  );
  static const String _heartbeatSecDefine = String.fromEnvironment(
    'HEARTBEAT_INTERVAL_SECONDS',
    defaultValue: '',
  );

  static String? _dot(String key) {
    final v = dotenv.env[key]?.trim();
    if (v == null || v.isEmpty) {
      return null;
    }
    return v;
  }

  /// URL API explicite (dart-define ou .env) ; `null` = laisser la résolution plateforme.
  static String? get explicitApiBaseUrl {
    if (_apiFromDefine.isNotEmpty) {
      return _apiFromDefine;
    }
    return _dot('API_BASE_URL');
  }

  /// URL affichée / stockée par défaut avant toute logique async.
  static String get initialApiBaseUrl =>
      explicitApiBaseUrl ?? 'http://127.0.0.1:8001';

  static String get supervisorLogoutCode {
    if (_logoutFromDefine.isNotEmpty) {
      return _logoutFromDefine;
    }
    return _dot('SUPERVISOR_LOGOUT_CODE') ?? '2026';
  }

  /// Hôte LAN optionnel depuis .env (si pas de --dart-define).
  static String get devApiHostFromDot => _dot('DEV_API_HOST') ?? '';

  static String get devApiPortFromDot => _dot('DEV_API_PORT') ?? '8001';

  /// Entre deux envois automatiques de heartbeat pendant une session ouverte.
  static Duration get heartbeatInterval {
    var sec = 60;
    if (_heartbeatSecDefine.isNotEmpty) {
      sec = int.tryParse(_heartbeatSecDefine.trim()) ?? sec;
    } else {
      final d = _dot('HEARTBEAT_INTERVAL_SECONDS');
      if (d != null) {
        sec = int.tryParse(d) ?? sec;
      }
    }
    sec = sec.clamp(30, 600);
    return Duration(seconds: sec);
  }
}
