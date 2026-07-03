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
import '../widgets/scan_frame_overlay.dart';

class ScanPage extends StatefulWidget {
  const ScanPage({super.key, this.isActive = true, this.onOpenMenu});

  /// Quand l’onglet Scanner n’est pas sélectionné, la caméra est arrêtée pour économiser batterie / éviter un aperçu actif en arrière-plan.
  final bool isActive;
  final VoidCallback? onOpenMenu;

  @override
  State<ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<ScanPage> with AutomaticKeepAliveClientMixin {
  final _scanService = ScanService();
  final _telemetry = DeviceTelemetryService();
  late final MobileScannerController _camera;

  String? _tokenQr;
  bool _loadingScan = false;
  String? _error;

  /// Vrai après un badgeage réussi : la caméra est arrêtée jusqu'à ce que
  /// l'utilisateur tape sur « Scanner à nouveau ».
  bool _cameraPaused = false;

  // Informations de position issues de /api/scan/secure/check-status/
  Map<String, dynamic>? _statusInfo;
  bool _loadingStatus = false;

  bool _geofenceBlocksBadge() {
    final info = _statusInfo;
    if (info == null) {
      return false;
    }
    final configured = info['geofence_configured'] == true;
    if (!configured) {
      return false;
    }
    final bool? inside = info['in_geofence'] as bool?;
    final bool? accuracyOk = info['accuracy_ok'] as bool?;
    final num? distance = info['distance_m'] as num?;
    if (accuracyOk == false) {
      return true;
    }
    if (distance == null || inside == null) {
      return true;
    }
    return inside != true;
  }

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
    if (widget.isActive && !_cameraPaused) {
      final allowed = await ensureCameraPermission(context);
      if (!mounted || !widget.isActive || _cameraPaused) {
        return;
      }
      if (allowed) {
        await _camera.start();
      }
    } else {
      await _camera.stop();
    }
  }

  Widget _buildPausedPlaceholder() {
    return ColoredBox(
      color: Colors.black87,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, size: 56, color: AppColors.ciGreen),
            const SizedBox(height: 12),
            Text(
              'Scan effectué',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _resumeScan,
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Scanner à nouveau'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildScannerHeader() {
    return Material(
      color: AppColors.ciGreenDark,
      child: SafeArea(
        bottom: false,
        child: SizedBox(
          height: kToolbarHeight,
          child: Row(
            children: [
              if (widget.onOpenMenu != null)
                IconButton(
                  icon: const Icon(Icons.menu, color: Colors.white),
                  onPressed: widget.onOpenMenu,
                )
              else
                const SizedBox(width: 8),
              Text(
                'Scanner',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 20,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBottomSheet(SessionProvider session) {
    final hasToken = _tokenQr != null && _tokenQr!.isNotEmpty;
    return Material(
      color: AppColors.cardBg,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      elevation: 8,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.borderColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: AppColors.iconQrBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.qr_code_scanner,
                    color: AppColors.ciGreenDark,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Scanner',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        hasToken
                            ? 'QR code détecté. Confirmez le badgeage ci-dessous.'
                            : 'Positionnez le QR code dans le cadre pour enregistrer une présence.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                              height: 1.35,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (hasToken) ...[
              const SizedBox(height: 12),
              _GeofenceBanner(
                info: _statusInfo,
                loading: _loadingStatus,
                onRefresh: _refreshStatus,
              ),
            ],
            if (session.isSecureHeartbeatRunning) ...[
              const SizedBox(height: 8),
              if (session.heartbeatGpsBlocked)
                _InfoStrip(
                  icon: Icons.location_off,
                  color: Colors.orange,
                  text:
                      'GPS indisponible — activez la localisation pour le suivi.',
                )
              else
                _InfoStrip(
                  icon: Icons.sensors,
                  color: AppColors.ciBlue,
                  text:
                      'Suivi de présence actif. Gardez l\u2019application au premier plan.',
                ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                _error!,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.error,
                  fontSize: 13,
                ),
              ),
            ],
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: (_loadingScan ||
                        !hasToken ||
                        _geofenceBlocksBadge())
                    ? null
                    : _doScan,
                icon: _loadingScan
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Icon(hasToken ? Icons.login : Icons.hourglass_empty),
                label: Text(
                  _loadingScan
                      ? 'Vérification…'
                      : _geofenceBlocksBadge()
                          ? 'Zone GPS non conforme'
                          : hasToken
                              ? 'Badger entrée / sortie'
                              : 'En attente du QR code…',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _resumeScan() async {
    setState(() {
      _cameraPaused = false;
      _tokenQr = null;
      _statusInfo = null;
      _error = null;
    });
    await _syncCameraWithTab();
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
            'Voulez-vous enregistrer votre sortie ?'
        : 'Voulez-vous enregistrer votre entrée$contexteSeance ?';
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
        await session.refreshMobileConfig();
        session.startSecureSessionHeartbeat(token);
      } else if (action == 'SORTIE' || action == 'SORTIE_AUTO') {
        session.stopSecureSessionHeartbeat();
      }
      session.requestHistoryRefresh();
      final confirmation = _confirmationMessage(action);
      // Caméra arrêtée tant que l'utilisateur n'a pas demandé un nouveau scan.
      await _camera.stop();
      if (!mounted) return;
      setState(() => _cameraPaused = true);
      if (mounted) {
        final isExit = action == 'SORTIE' || action == 'SORTIE_AUTO';
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            icon: Icon(
              Icons.check_circle,
              color: isExit ? Colors.red.shade700 : AppColors.ciGreenDark,
              size: 48,
            ),
            title: const Text('Scan effectué'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Action enregistrée :',
                  style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                        color: AppColors.textMuted,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  confirmation,
                  style: Theme.of(ctx).textTheme.bodyLarge,
                ),
              ],
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

  void _onQrDetected(String code) {
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
                  'QR code détecté — confirmez le badgeage.',
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final session = context.watch<SessionProvider>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildScannerHeader(),
        Expanded(
          child: Stack(
            fit: StackFit.expand,
            children: [
              ColoredBox(
                color: Colors.black,
                child: _cameraPaused
                    ? _buildPausedPlaceholder()
                    : MobileScanner(
                        controller: _camera,
                        onDetect: (capture) {
                          final code = capture.barcodes.first.rawValue;
                          if (code == null || code.isEmpty) {
                            return;
                          }
                          _onQrDetected(code);
                        },
                      ),
              ),
              if (!_cameraPaused) const ScanFrameOverlay(),
            ],
          ),
        ),
        _buildBottomSheet(session),
      ],
    );
  }
}

class _InfoStrip extends StatelessWidget {
  const _InfoStrip({
    required this.icon,
    required this.color,
    required this.text,
  });

  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
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
