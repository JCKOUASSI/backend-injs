import 'dart:async';

import 'package:flutter/foundation.dart';

import '../config/app_env.dart';
import '../services/auth_service.dart';
import '../services/background_keepalive.dart';
import '../services/device_telemetry_service.dart';
import '../services/scan_service.dart';
import '../services/storage_service.dart';
import '../utils/dev_api_defaults.dart';

class SessionProvider extends ChangeNotifier {
  final StorageService _storage = StorageService();
  final AuthService _auth = AuthService();
  final ScanService _heartbeatScan = ScanService();
  final DeviceTelemetryService _heartbeatTelemetry = DeviceTelemetryService();

  Timer? _heartbeatTimer;
  String? _heartbeatTokenQr;
  bool _heartbeatBusy = false;
  int _heartbeatGpsMisses = 0;
  static const _kGpsMissThreshold = 3;

  bool isBootstrapping = true;
  bool isAuthenticated = false;
  String baseUrl = AppEnv.initialApiBaseUrl;
  String? accessToken;
  String? refreshToken;
  String? username;
  String? deviceId;
  Map<String, dynamic>? user;
  bool mustChangePassword = false;

  /// Résultat de la demande de permission GPS au démarrage.
  /// Initialisé à `true` pour éviter un flash d'avertissement avant
  /// que la permission ait été vérifiée.
  bool gpsGranted = true;

  /// Vrai quand le heartbeat échoue ≥ [_kGpsMissThreshold] fois de suite
  /// faute de position GPS disponible.
  bool heartbeatGpsBlocked = false;

  /// Heartbeat automatique actif (après une entrée, jusqu'à sortie ou fin de session).
  bool get isSecureHeartbeatRunning => _heartbeatTimer != null;

  /// Notifie l'app du résultat de la demande de permission GPS.
  void setGpsGranted(bool granted) {
    if (gpsGranted == granted) return;
    gpsGranted = granted;
    notifyListeners();
  }

  /// Démarre l'envoi périodique de `/api/scan/secure/heartbeat/` pour le QR courant.
  void startSecureSessionHeartbeat(String tokenQr) {
    stopSecureSessionHeartbeat();
    final t = tokenQr.trim();
    if (t.isEmpty) {
      return;
    }
    _heartbeatTokenQr = t;
    final every = AppEnv.heartbeatInterval;
    void schedulePulse() {
      scheduleMicrotask(_heartbeatPulse);
    }

    schedulePulse();
    _heartbeatTimer = Timer.periodic(every, (_) => schedulePulse());
    // Garde l'app vivante en arrière-plan (foreground service Android,
    // background location iOS) tant que la session est ouverte.
    unawaited(BackgroundKeepalive.instance.start());
    notifyListeners();
  }

  /// Déclenche immédiatement un pulse de heartbeat (sans attendre le timer).
  /// Utile au retour d'arrière-plan pour rattraper un éventuel délai Doze.
  void pulseHeartbeatNow() {
    if (_heartbeatTimer == null) {
      return;
    }
    scheduleMicrotask(_heartbeatPulse);
  }

  void stopSecureSessionHeartbeat({bool notify = true}) {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _heartbeatTokenQr = null;
    _heartbeatBusy = false;
    _heartbeatGpsMisses = 0;
    heartbeatGpsBlocked = false;
    unawaited(BackgroundKeepalive.instance.stop());
    if (notify) {
      notifyListeners();
    }
  }

  Future<void> _heartbeatPulse() async {
    if (_heartbeatBusy) {
      return;
    }
    final token = _heartbeatTokenQr;
    final tokenAccess = accessToken;
    final dev = deviceId;
    if (token == null ||
        token.isEmpty ||
        tokenAccess == null ||
        tokenAccess.isEmpty ||
        dev == null ||
        dev.isEmpty) {
      stopSecureSessionHeartbeat();
      return;
    }
    _heartbeatBusy = true;
    try {
      final tel = await _heartbeatTelemetry.capture();
      if (!tel.hasPosition) {
        _heartbeatGpsMisses++;
        if (_heartbeatGpsMisses >= _kGpsMissThreshold && !heartbeatGpsBlocked) {
          heartbeatGpsBlocked = true;
          notifyListeners();
        }
        return;
      }
      // GPS OK : réinitialise le compteur de ratés.
      if (_heartbeatGpsMisses > 0 || heartbeatGpsBlocked) {
        _heartbeatGpsMisses = 0;
        heartbeatGpsBlocked = false;
        notifyListeners();
      }
      final res = await _heartbeatScan.heartbeat(
        baseUrl: baseUrl,
        accessToken: tokenAccess,
        tokenQr: token,
        deviceId: dev,
        latitude: tel.latitude!,
        longitude: tel.longitude!,
        accuracyM: tel.accuracyM,
        batteryLevel: tel.batteryLevel,
        isCharging: tel.isCharging,
      );
      if (res['action']?.toString() == 'SORTIE_AUTO') {
        stopSecureSessionHeartbeat();
      }
    } catch (e, st) {
      final msg = e.toString();
      debugPrint('[qr_badge.session] Heartbeat auto: $e\n$st');
      if (msg.contains('NO_OPEN_SESSION') ||
          msg.contains('Aucune session ouverte') ||
          msg.contains('SESSION_TERMINATED') ||
          msg.contains('TOKEN_EXPIRED') ||
          msg.contains('INVALID_TOKEN')) {
        stopSecureSessionHeartbeat();
      }
    } finally {
      _heartbeatBusy = false;
    }
  }

  Future<void> bootstrap() async {
    isBootstrapping = true;
    notifyListeners();
    baseUrl = await _resolveBaseUrlFromEnv();
    accessToken = await _storage.getAccessToken();
    refreshToken = await _storage.getRefreshToken();
    username = await _storage.getUsername();
    deviceId = await _storage.getOrCreateDeviceId();
    mustChangePassword = await _storage.getMustChangePassword();
    isAuthenticated = accessToken != null && accessToken!.isNotEmpty;
    if (isAuthenticated) {
      try {
        final me = await _auth.me(baseUrl: baseUrl, accessToken: accessToken!);
        user = me;
        mustChangePassword = _readMustChangePassword(<String, dynamic>{}, user);
        await _storage.setMustChangePassword(mustChangePassword);
      } catch (_) {
        // Token probablement expiré — tenter un refresh silencieux.
        final refreshed = await tryRefreshToken();
        if (refreshed) {
          try {
            final me = await _auth.me(baseUrl: baseUrl, accessToken: accessToken!);
            user = me;
            mustChangePassword = _readMustChangePassword(<String, dynamic>{}, user);
            await _storage.setMustChangePassword(mustChangePassword);
          } catch (_) {
            // Hors-ligne après refresh : conserver le dernier état local.
          }
        }
      }
    }
    isBootstrapping = false;
    notifyListeners();
  }

  /// Priorité : dart-define > app.env > fallback.
  Future<String> _resolveBaseUrlFromEnv() async {
    final explicit = AppEnv.explicitApiBaseUrl;
    if (explicit != null && explicit.isNotEmpty) {
      return explicit;
    }
    return DevApiDefaults.resolve();
  }

  Future<void> login({
    required String usernameInput,
    required String passwordInput,
  }) async {
    final id = deviceId ?? await _storage.getOrCreateDeviceId();
    late final Map<String, dynamic> payload;
    try {
      payload = await _auth.login(
        baseUrl: baseUrl,
        username: usernameInput.trim(),
        password: passwordInput,
        deviceId: id,
      );
    } catch (e, st) {
      debugPrint('[qr_badge.session] Connexion échouée: $e');
      debugPrint('$st');
      rethrow;
    }
    final access = payload['access']?.toString() ?? '';
    final refresh = payload['refresh']?.toString() ?? '';
    if (access.isEmpty || refresh.isEmpty) {
      throw Exception('Réponse de connexion invalide.');
    }

    accessToken = access;
    refreshToken = refresh;
    user = payload['user'] is Map<String, dynamic>
        ? payload['user'] as Map<String, dynamic>
        : null;
    username = usernameInput.trim();
    deviceId = id;
    mustChangePassword = _readMustChangePassword(payload, user);

    await _storage.saveTokens(access: access, refresh: refresh);
    await _storage.setUsername(username!);
    await _storage.setMustChangePassword(mustChangePassword);
    isAuthenticated = true;
    notifyListeners();
  }

  /// Tente de rafraîchir le token d'accès avec le refresh token.
  /// Retourne true si le rafraîchissement a réussi, false sinon.
  Future<bool> tryRefreshToken() async {
    final rt = refreshToken;
    if (rt == null || rt.isEmpty) {
      return false;
    }
    try {
      final payload = await _auth.refreshToken(baseUrl: baseUrl, refreshToken: rt);
      final newAccess = payload['access']?.toString() ?? '';
      if (newAccess.isEmpty) {
        return false;
      }
      accessToken = newAccess;
      await _storage.saveTokens(access: newAccess, refresh: rt);
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {
    final token = accessToken;
    if (token == null || token.isEmpty) {
      throw Exception('Session expirée. Reconnectez-vous.');
    }
    await _auth.changePassword(
      baseUrl: baseUrl,
      accessToken: token,
      oldPassword: oldPassword,
      newPassword: newPassword,
    );
    mustChangePassword = false;
    if (user != null) {
      user = Map<String, dynamic>.from(user!);
      user!['must_change_password'] = false;
    }
    await _storage.setMustChangePassword(false);
    notifyListeners();
  }

  Future<void> logout() async {
    stopSecureSessionHeartbeat();
    await _storage.clearTokens();
    accessToken = null;
    refreshToken = null;
    user = null;
    mustChangePassword = false;
    isAuthenticated = false;
    notifyListeners();
  }

  bool _readMustChangePassword(
    Map<String, dynamic> payload,
    Map<String, dynamic>? userMap,
  ) {
    final top = payload['must_change_password'];
    if (top is bool) {
      return top;
    }
    if (top is String) {
      return top.toLowerCase() == 'true';
    }
    final fromUser = userMap?['must_change_password'];
    if (fromUser is bool) {
      return fromUser;
    }
    if (fromUser is String) {
      return fromUser.toLowerCase() == 'true';
    }
    return false;
  }

  @override
  void dispose() {
    stopSecureSessionHeartbeat(notify: false);
    super.dispose();
  }
}
