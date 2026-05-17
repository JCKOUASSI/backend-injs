import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Timeout appliqué à chaque requête réseau.
/// 10 s est suffisant sur un LAN ; au-delà le serveur est considéré injoignable.
const _kTimeout = Duration(seconds: 10);

class ApiClient {
  ApiClient({
    required this.baseUrl,
    this.accessToken,
    this.onRefreshToken,
  });

  final String baseUrl;
  final String? accessToken;

  /// Callback optionnel appelé quand le serveur renvoie 401.
  /// Doit retourner le nouveau token d'accès, ou null si le refresh a échoué.
  final Future<String?> Function()? onRefreshToken;

  Uri _uri(String path) {
    final normalizedBase = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$normalizedBase$normalizedPath');
  }

  Map<String, String> _headers({bool withAuth = true}) {
    return {
      'Content-Type': 'application/json',
      if (withAuth && accessToken != null && accessToken!.isNotEmpty)
        'Authorization': 'Bearer $accessToken',
    };
  }

  Map<String, String> _headersWithToken(String token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? data,
    bool withAuth = true,
  }) async {
    final uri = _uri(path);
    try {
      final res = await http
          .post(
            uri,
            headers: _headers(withAuth: withAuth),
            body: jsonEncode(data ?? <String, dynamic>{}),
          )
          .timeout(_kTimeout);
      if (res.statusCode == 401 && withAuth && onRefreshToken != null) {
        debugPrint('[qr_badge.api] POST $path \u2192 401, tentative de refresh...');
        final newToken = await onRefreshToken!();
        if (newToken != null) {
          debugPrint('[qr_badge.api] POST $path \u2192 refresh OK, retry...');
          final retryRes = await http
              .post(
                uri,
                headers: _headersWithToken(newToken),
                body: jsonEncode(data ?? <String, dynamic>{}),
              )
              .timeout(_kTimeout);
          return _parse(retryRes, method: 'POST', path: path, uri: uri);
        }
        debugPrint('[qr_badge.api] POST $path \u2192 refresh \u00e9chou\u00e9, session expir\u00e9e.');
        throw const SessionExpiredException();
      }
      return _parse(res, method: 'POST', path: path, uri: uri);
    } on SessionExpiredException {
      rethrow;
    } on ApiResponseException {
      rethrow;
    } on TimeoutException {
      debugPrint('[qr_badge.api] POST $path \u2192 timeout (${_kTimeout.inSeconds}s)');
      throw NetworkTimeoutException(uri.host, uri.port);
    } catch (e, st) {
      debugPrint('[qr_badge.api] POST $path \u2192 erreur r\u00e9seau: $e');
      debugPrint('$st');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> get(
    String path, {
    bool withAuth = true,
  }) async {
    final uri = _uri(path);
    try {
      final res = await http
          .get(
            uri,
            headers: _headers(withAuth: withAuth),
          )
          .timeout(_kTimeout);
      if (res.statusCode == 401 && withAuth && onRefreshToken != null) {
        debugPrint('[qr_badge.api] GET $path \u2192 401, tentative de refresh...');
        final newToken = await onRefreshToken!();
        if (newToken != null) {
          debugPrint('[qr_badge.api] GET $path \u2192 refresh OK, retry...');
          final retryRes = await http
              .get(
                uri,
                headers: _headersWithToken(newToken),
              )
              .timeout(_kTimeout);
          return _parse(retryRes, method: 'GET', path: path, uri: uri);
        }
        debugPrint('[qr_badge.api] GET $path \u2192 refresh \u00e9chou\u00e9, session expir\u00e9e.');
        throw const SessionExpiredException();
      }
      return _parse(res, method: 'GET', path: path, uri: uri);
    } on SessionExpiredException {
      rethrow;
    } on ApiResponseException {
      rethrow;
    } on TimeoutException {
      debugPrint('[qr_badge.api] GET $path \u2192 timeout (${_kTimeout.inSeconds}s)');
      throw NetworkTimeoutException(uri.host, uri.port);
    } catch (e, st) {
      debugPrint('[qr_badge.api] GET $path \u2192 erreur r\u00e9seau: $e');
      debugPrint('$st');
      rethrow;
    }
  }

  Map<String, dynamic> _parse(
    http.Response res, {
    required String method,
    required String path,
    required Uri uri,
  }) {
    Map<String, dynamic> json = <String, dynamic>{};
    if (res.body.isNotEmpty) {
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) {
          json = decoded;
        } else {
          json = {'data': decoded};
        }
      } catch (_) {
        final trimmed = res.body.trimLeft();
        if (trimmed.startsWith('<!DOCTYPE') ||
            trimmed.startsWith('<html') ||
            trimmed.startsWith('<')) {
          throw ApiResponseException(
            statusCode: res.statusCode,
            path: path,
            message: res.statusCode == 404
                ? 'Ressource introuvable ($path). '
                    'Vérifiez que le serveur Django est à jour et redémarré.'
                : 'Réponse HTML inattendue du serveur (HTTP ${res.statusCode}).',
          );
        }
        rethrow;
      }
    }
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json;
    }
    final bodyPreview = res.body.length > 800
        ? '${res.body.substring(0, 800)}\u2026'
        : res.body;
    debugPrint(
      '[qr_badge.api] $method $path \u2192 HTTP ${res.statusCode} uri=$uri body=$bodyPreview',
    );
    if (json['code']?.toString() == 'PASSWORD_CHANGE_REQUIRED') {
      throw Exception(
        json['detail']?.toString() ??
            'Vous devez changer votre mot de passe avant de continuer.',
      );
    }
    final detail = json['detail']?.toString() ??
        json['message']?.toString() ??
        _firstFieldError(json) ??
        'Erreur API (${res.statusCode})';
    throw Exception(detail);
  }

  String? _firstFieldError(Map<String, dynamic> body) {
    for (final entry in body.entries) {
      final v = entry.value;
      if (v is List && v.isNotEmpty) {
        return v.first.toString();
      }
      if (v is String && v.isNotEmpty) {
        return v;
      }
    }
    return null;
  }
}

/// Exception levée quand une requête d\u00e9passe [_kTimeout].
class NetworkTimeoutException implements Exception {
  const NetworkTimeoutException(this.host, this.port);
  final String host;
  final int port;

  @override
  String toString() =>
      'Serveur injoignable \u2014 aucune r\u00e9ponse de $host:$port '
      'apr\u00e8s ${_kTimeout.inSeconds}\u00a0s.\n'
      'V\u00e9rifiez que le serveur est d\u00e9marr\u00e9 et que l\u2019URL '
      'dans \u00ab\u00a0Configurer le serveur\u00a0\u00bb est correcte.';
}

/// Exception publique pour que les appelants puissent capturer la session expir\u00e9e.
class SessionExpiredException implements Exception {
  const SessionExpiredException();
  @override
  String toString() => 'Session expir\u00e9e. Veuillez vous reconnecter.';
}

/// Réponse HTTP non JSON (souvent une page 404 HTML Django).
class ApiResponseException implements Exception {
  const ApiResponseException({
    required this.statusCode,
    required this.path,
    required this.message,
  });

  final int statusCode;
  final String path;
  final String message;

  @override
  String toString() => message;
}
