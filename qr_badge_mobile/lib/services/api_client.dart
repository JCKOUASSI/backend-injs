import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

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
      final res = await http.post(
        uri,
        headers: _headers(withAuth: withAuth),
        body: jsonEncode(data ?? <String, dynamic>{}),
      );
      if (res.statusCode == 401 && withAuth && onRefreshToken != null) {
        debugPrint('[qr_badge.api] POST $path → 401, tentative de refresh...');
        final newToken = await onRefreshToken!();
        if (newToken != null) {
          debugPrint('[qr_badge.api] POST $path → refresh OK, retry...');
          final retryRes = await http.post(
            uri,
            headers: _headersWithToken(newToken),
            body: jsonEncode(data ?? <String, dynamic>{}),
          );
          return _parse(retryRes, method: 'POST', path: path, uri: uri);
        }
        debugPrint('[qr_badge.api] POST $path → refresh échoué, session expirée.');
        throw const SessionExpiredException();
      }
      return _parse(res, method: 'POST', path: path, uri: uri);
    } on SessionExpiredException {
      rethrow;
    } catch (e, st) {
      debugPrint('[qr_badge.api] POST $path → erreur réseau: $e');
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
      final res = await http.get(
        uri,
        headers: _headers(withAuth: withAuth),
      );
      if (res.statusCode == 401 && withAuth && onRefreshToken != null) {
        debugPrint('[qr_badge.api] GET $path → 401, tentative de refresh...');
        final newToken = await onRefreshToken!();
        if (newToken != null) {
          debugPrint('[qr_badge.api] GET $path → refresh OK, retry...');
          final retryRes = await http.get(
            uri,
            headers: _headersWithToken(newToken),
          );
          return _parse(retryRes, method: 'GET', path: path, uri: uri);
        }
        debugPrint('[qr_badge.api] GET $path → refresh échoué, session expirée.');
        throw const SessionExpiredException();
      }
      return _parse(res, method: 'GET', path: path, uri: uri);
    } on SessionExpiredException {
      rethrow;
    } catch (e, st) {
      debugPrint('[qr_badge.api] GET $path → erreur réseau: $e');
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
      final decoded = jsonDecode(res.body);
      if (decoded is Map<String, dynamic>) {
        json = decoded;
      } else {
        json = {'data': decoded};
      }
    }
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return json;
    }
    final bodyPreview = res.body.length > 800
        ? '${res.body.substring(0, 800)}…'
        : res.body;
    debugPrint(
      '[qr_badge.api] $method $path → HTTP ${res.statusCode} uri=$uri body=$bodyPreview',
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

/// Exception publique pour que les appelants puissent capturer la session expirée.
class SessionExpiredException implements Exception {
  const SessionExpiredException();
  @override
  String toString() => 'Session expirée. Veuillez vous reconnecter.';
}
