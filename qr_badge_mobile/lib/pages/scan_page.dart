import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/device_telemetry_service.dart';
import '../services/scan_service.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/camera_permission.dart';
import '../utils/confirm_dialog.dart';

class ScanPage extends StatefulWidget {
  const ScanPage({super.key, this.isActive = true});

  /// Quand l’onglet Scanner n’est pas sélectionné, la caméra est arrêtée pour économiser batterie / éviter un aperçu actif en arrière-plan.
  final bool isActive;

  @override
  State<ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<ScanPage> with AutomaticKeepAliveClientMixin {
  final _scanService = ScanService();
  final _telemetry = DeviceTelemetryService();
  late final MobileScannerController _camera;

  String? _tokenQr;
  bool _loadingScan = false;
  String? _result;
  String? _error;

  // Informations de position issues de /api/scan/secure/check-status/
  Map<String, dynamic>? _statusInfo;
  bool _loadingStatus = false;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _camera = MobileScannerController(autoStart: false);
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncCameraWithTab());
  }

  @override
  void didUpdateWidget(covariant ScanPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isActive != widget.isActive) {
      _syncCameraWithTab();
    }
  }

  Future<void> _syncCameraWithTab() async {
    if (!mounted) {
      return;
    }
    if (widget.isActive) {
      final allowed = await ensureCameraPermission(context);
      if (!mounted || !widget.isActive) {
        return;
      }
      if (allowed) {
        await _camera.start();
      }
    } else {
      await _camera.stop();
    }
  }

  Future<void> _refreshStatus() async {
    final session = context.read<SessionProvider>();
    final token = _tokenQr?.trim() ?? '';
    if (token.isEmpty || session.accessToken == null) {
      return;
    }
    setState(() => _loadingStatus = true);
    try {
      final tel = await _telemetry.capture();
      final statut = await _scanService.checkSecureStatus(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        tokenQr: token,
        latitude: tel.latitude,
        longitude: tel.longitude,
        accuracyM: tel.accuracyM,
      );
      if (mounted) {
        setState(() => _statusInfo = statut);
      }
    } catch (_) {
      // silencieux : si le serveur est injoignable, le bandeau l'indiquera via _error lors du badgeage.
    } finally {
      if (mounted) {
        setState(() => _loadingStatus = false);
      }
    }
  }

  String _extractToken(String raw) {
    final parsed = Uri.tryParse(raw.trim());
    if (parsed != null && parsed.queryParameters.containsKey('token')) {
      return parsed.queryParameters['token'] ?? raw.trim();
    }
    return raw.trim();
  }

  Future<void> _doScan() async {
    final session = context.read<SessionProvider>();
    final token = _tokenQr?.trim() ?? '';
    if (token.isEmpty) {
      setState(() => _error = 'Scannez d’abord le QR code de la séance.');
      return;
    }
    if (session.accessToken == null || session.deviceId == null) {
      setState(() => _error = 'Session invalide, reconnectez-vous.');
      return;
    }
    // 1) Vérifier auprès du serveur si le prochain badge est une ENTREE ou une SORTIE.
    setState(() {
      _loadingScan = true;
      _error = null;
      _result = null;
    });
    String? actionSuivante;
    String? heureEntree;
    String? seanceLabel;
    try {
      // Capture la position avant checkSecureStatus pour cohérence avec _refreshStatus.
      final telPre = await _telemetry.capture();
      final statut = await _scanService.checkSecureStatus(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        tokenQr: token,
        latitude: telPre.latitude,
        longitude: telPre.longitude,
        accuracyM: telPre.accuracyM,
      );
      actionSuivante = statut['action_suivante']?.toString();
      heureEntree = statut['heure_entree']?.toString();
      seanceLabel = statut['seance_intitule']?.toString();
      if (statut['statut']?.toString() == 'TERMINE') {
        setState(() {
          _loadingScan = false;
          _error =
              'Vous avez déjà pointé (entrée et sortie) pour cette séance.';
        });
        return;
      }
    } catch (e) {
      setState(() => _loadingScan = false);
      if (mounted) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Serveur injoignable'),
            content: Text(
              'Impossible de vérifier le statut de badgeage.\n\n'
              '${e.toString().replaceFirst('Exception: ', '')}\n\n'
              'Vérifiez que le téléphone et l\u2019ordinateur sont sur le même réseau '
              'et que API_BASE_URL dans app.env pointe vers l\u2019IP LAN du Mac '
              '(ex. http://192.168.x.x:8001).',
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
      return;
    }
    if (!mounted) {
      return;
    }
    setState(() => _loadingScan = false);

    final willExit = actionSuivante == 'SORTIE';
    final isExit = willExit;
    final titre = isExit ? 'Confirmer la sortie' : 'Confirmer l\u2019entrée';
    final bouton =
        isExit ? 'Badger la sortie' : 'Badger l\u2019entrée';
    final contexteSeance =
        (seanceLabel != null && seanceLabel.isNotEmpty) ? ' « $seanceLabel »' : '';
    final message = isExit
        ? 'Vous êtes actuellement en salle'
            '${heureEntree != null && heureEntree.isNotEmpty ? ' depuis $heureEntree' : ''}'
            '$contexteSeance.\n'
            'Voulez-vous enregistrer votre sortie ?\n'
            'Votre position GPS et l\u2019état de la batterie seront envoyés.'
        : 'Voulez-vous enregistrer votre entrée$contexteSeance ?\n'
            'Votre position GPS et l\u2019état de la batterie seront envoyés.';
    final ok = await confirm(
      context,
      title: titre,
      message: message,
      confirmLabel: bouton,
      destructive: isExit,
    );
    if (!ok || !mounted) {
      return;
    }
    setState(() {
      _loadingScan = true;
      _error = null;
      _result = null;
    });
    try {
      final tel = await _telemetry.capture();
      final res = await _scanService.secureScan(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        tokenQr: token,
        deviceId: session.deviceId!,
        latitude: tel.latitude,
        longitude: tel.longitude,
        accuracyM: tel.accuracyM,
        batteryLevel: tel.batteryLevel,
        isCharging: tel.isCharging,
      );
      final action = res['action']?.toString();
      if (action == 'ENTREE') {
        session.startSecureSessionHeartbeat(token);
      } else if (action == 'SORTIE' || action == 'SORTIE_AUTO') {
        session.stopSecureSessionHeartbeat();
      }
      final confirmation = _confirmationMessage(action);
      setState(() => _result = confirmation);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(confirmation)),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) {
        setState(() => _loadingScan = false);
      }
    }
  }

  String _confirmationMessage(String? action) {
    switch (action) {
      case 'ENTREE':
        return 'Entrée enregistrée. Le suivi de présence est actif.';
      case 'SORTIE':
        return 'Sortie enregistrée. Le suivi de présence est arrêté.';
      case 'SORTIE_AUTO':
        return 'Sortie automatique enregistrée (session fermée).';
      default:
        return 'Badgeage enregistré.';
    }
  }

  @override
  void dispose() {
    _camera.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final session = context.watch<SessionProvider>();
    return LayoutBuilder(
      builder: (context, constraints) {
        final previewHeight = (constraints.maxHeight * 0.42).clamp(220.0, 360.0);
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            Center(
              child: Icon(Icons.qr_code_2, size: 44, color: AppColors.accentOrange),
            ),
            const SizedBox(height: 8),
            Text(
              'Scannez le QR code',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.textPrimary,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              'Pointez votre caméra vers le QR code affiché par le superviseur',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textMuted,
                  ),
            ),
            const SizedBox(height: 18),
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Container(
                height: previewHeight,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.ciGreenDark, width: 2),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: MobileScanner(
                    controller: _camera,
                    onDetect: (capture) {
                      final code = capture.barcodes.first.rawValue;
                      if (code == null || code.isEmpty) {
                        return;
                      }
                      final t = _extractToken(code);
                      if (t.isEmpty || t == _tokenQr) {
                        return;
                      }
                      HapticFeedback.mediumImpact();
                      setState(() {
                        _tokenQr = t;
                        _error = null;
                        _statusInfo = null;
                      });
                      _refreshStatus();
                      ScaffoldMessenger.of(context)
                        ..hideCurrentSnackBar()
                        ..showSnackBar(
                          const SnackBar(
                            duration: Duration(seconds: 2),
                            backgroundColor: AppColors.ciGreenDark,
                            content: Row(
                              children: [
                                Icon(Icons.check_circle, color: Colors.white),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'QR code détecté — appuyez sur « Badger » pour confirmer.',
                                    style: TextStyle(color: Colors.white),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                    },
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: (_tokenQr != null && _tokenQr!.isNotEmpty)
                    ? AppColors.ciGreen.withValues(alpha: 0.15)
                    : Colors.grey.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: (_tokenQr != null && _tokenQr!.isNotEmpty)
                      ? AppColors.ciGreenDark
                      : Colors.grey.shade400,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    (_tokenQr != null && _tokenQr!.isNotEmpty)
                        ? Icons.check_circle
                        : Icons.qr_code_scanner,
                    color: (_tokenQr != null && _tokenQr!.isNotEmpty)
                        ? AppColors.ciGreenDark
                        : AppColors.textMuted,
                    size: 22,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      (_tokenQr != null && _tokenQr!.isNotEmpty)
                          ? 'QR code détecté. Appuyez sur « Badger » pour confirmer.'
                          : 'En attente — pointez la caméra vers le QR code.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontWeight: FontWeight.w500,
                          ),
                    ),
                  ),
                ],
              ),
            ),
            if (_tokenQr != null && _tokenQr!.isNotEmpty) ...[
              const SizedBox(height: 8),
              _GeofenceBanner(
                info: _statusInfo,
                loading: _loadingStatus,
                onRefresh: _refreshStatus,
              ),
            ],
            if (session.isSecureHeartbeatRunning) ...[
              const SizedBox(height: 8),
              // Bandeau GPS bloqué : 3 heartbeats consécutifs sans position.
              if (session.heartbeatGpsBlocked)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.orange.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.orange),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.location_off,
                          color: Colors.orange.shade800, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'GPS indisponible — le suivi de présence ne peut pas envoyer votre position. '
                          'Activez la localisation pour que le heartbeat fonctionne.',
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Colors.orange.shade900,
                                  ),
                        ),
                      ),
                    ],
                  ),
                )
              else
                Row(
                  children: [
                    const Icon(Icons.sensors,
                        color: AppColors.ciBlue, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Suivi de présence actif (GPS requis). '
                        'Gardez l\u2019application au premier plan pour que le suivi continue.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  ],
                ),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: (_loadingScan || _tokenQr == null || _tokenQr!.isEmpty)
                    ? null
                    : _doScan,
                icon: _loadingScan
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : Icon(
                        (_tokenQr != null && _tokenQr!.isNotEmpty)
                            ? Icons.login
                            : Icons.hourglass_empty,
                      ),
                label: Text(
                  _loadingScan
                      ? 'Vérification…'
                      : (_tokenQr != null && _tokenQr!.isNotEmpty)
                          ? 'Badger entrée / sortie'
                          : 'En attente du QR code…',
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13),
              ),
            ],
            if (_result != null) ...[
              const SizedBox(height: 8),
              SelectableText(
                _result!,
                style: const TextStyle(color: AppColors.ciGreenDark, fontSize: 13),
              ),
            ],
          ],
        );
      },
    );
  }
}

class _GeofenceBanner extends StatelessWidget {
  const _GeofenceBanner({
    required this.info,
    required this.loading,
    required this.onRefresh,
  });

  final Map<String, dynamic>? info;
  final bool loading;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    // État initial : en cours de chargement / pas encore de réponse.
    if (info == null) {
      return _wrap(
        context: context,
        color: Colors.grey.withValues(alpha: 0.12),
        border: Colors.grey.shade400,
        icon: Icons.my_location,
        iconColor: AppColors.textMuted,
        title: loading
            ? 'Calcul de votre position en cours…'
            : 'Position non vérifiée.',
        subtitle: null,
      );
    }

    final bool configured = info!['geofence_configured'] == true;
    if (!configured) {
      return _wrap(
        context: context,
        color: AppColors.ciBlue.withValues(alpha: 0.10),
        border: AppColors.ciBlue,
        icon: Icons.info_outline,
        iconColor: AppColors.ciBlue,
        title: 'Aucune zone GPS définie pour ce module.',
        subtitle:
            'Le badgeage ne contrôle pas la position pour cette séance.',
      );
    }

    final num? distance = info!['distance_m'] as num?;
    final bool? inside = info!['in_geofence'] as bool?;
    final bool? accuracyOk = info!['accuracy_ok'] as bool?;

    if (distance == null || inside == null) {
      return _wrap(
        context: context,
        color: Colors.orange.withValues(alpha: 0.12),
        border: Colors.orange,
        icon: Icons.location_searching,
        iconColor: Colors.orange.shade800,
        title: 'Position GPS indisponible.',
        subtitle:
            'Activez la localisation et sortez à l\u2019extérieur pour capter le signal.',
        trailing: _refreshBtn(),
      );
    }

    if (accuracyOk == false) {
      return _wrap(
        context: context,
        color: Colors.orange.withValues(alpha: 0.15),
        border: Colors.orange,
        icon: Icons.gps_not_fixed,
        iconColor: Colors.orange.shade800,
        title: 'Signal GPS imprécis.',
        subtitle:
            'Sortez à l\u2019extérieur pour améliorer la précision.',
        trailing: _refreshBtn(),
      );
    }

    if (inside) {
      return _wrap(
        context: context,
        color: AppColors.ciGreen.withValues(alpha: 0.15),
        border: AppColors.ciGreenDark,
        icon: Icons.gps_fixed,
        iconColor: AppColors.ciGreenDark,
        title: 'Vous êtes dans la zone de badgeage.',
        subtitle: null,
        trailing: _refreshBtn(),
      );
    }

    return _wrap(
      context: context,
      color: Colors.red.withValues(alpha: 0.12),
      border: Colors.red,
      icon: Icons.wrong_location,
      iconColor: Colors.red.shade700,
      title: 'Hors zone — rapprochez-vous du site.',
      subtitle: null,
      trailing: _refreshBtn(),
    );
  }

  Widget _refreshBtn() {
    return IconButton(
      tooltip: 'Recalculer la position',
      icon: loading
          ? const SizedBox(
              height: 18,
              width: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.refresh, size: 20),
      onPressed: loading ? null : onRefresh,
    );
  }

  Widget _wrap({
    required BuildContext context,
    required Color color,
    required Color border,
    required IconData icon,
    required Color iconColor,
    required String title,
    String? subtitle,
    Widget? trailing,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(icon, color: iconColor, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                  ),
                ],
              ],
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}
