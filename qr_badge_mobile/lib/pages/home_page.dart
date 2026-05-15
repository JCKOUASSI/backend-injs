import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/guarded_logout.dart';
import '../utils/open_privacy_policy.dart';
import 'history_page.dart';
import 'login_page.dart';
import 'scan_page.dart';

String _rolePillLabel(Map<String, dynamic>? user) {
  final r = user?['role']?.toString() ?? '';
  switch (r) {
    case 'AUDITEUR':
      return 'Participant';
    case 'ENCADRANT':
      return 'Encadrant';
    case 'SECRETARIAT':
    case 'CHEF_SECRETARIAT':
      return 'Secretariat';
    case 'CPFAE_ADMIN':
      return 'CPFAE';
    case 'CHEF_CPFAE_ADMIN':
      return 'Chef CPFAE';
    case 'DIRECTION':
      return 'Direction';
    case 'ADMIN':
      return 'Administrateur';
    default:
      return r.isEmpty ? 'Utilisateur' : r;
  }
}

String _displayName(SessionProvider session) {
  final u = session.user;
  if (u != null) {
    final fn = (u['first_name'] ?? '').toString().trim();
    final ln = (u['last_name'] ?? '').toString().trim();
    final full = '$fn $ln'.trim();
    if (full.isNotEmpty) {
      return full;
    }
  }
  return session.user?['username']?.toString() ?? session.username ?? '\u2014';
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Le heartbeat continue de tourner via Timer.periodic tant que le process
    // est vivant (best-effort en arrière-plan). Au retour, on déclenche un
    // pulse immédiat pour rattraper un éventuel délai (Doze, throttling).
    if (state == AppLifecycleState.resumed) {
      context.read<SessionProvider>().pulseHeartbeatNow();
    }
  }

  Future<void> _requestGps(SessionProvider session) async {
    final serviceOn = await Geolocator.isLocationServiceEnabled();
    if (!serviceOn) {
      if (mounted) Geolocator.openLocationSettings();
      return;
    }
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.deniedForever) {
      if (mounted) openAppSettings();
      return;
    }
    if (perm != LocationPermission.always &&
        perm != LocationPermission.whileInUse) {
      perm = await Geolocator.requestPermission();
    }
    if (mounted) {
      final granted = perm == LocationPermission.always ||
          perm == LocationPermission.whileInUse;
      session.setGpsGranted(granted);
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('QR Badge'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: (value) async {
              if (value == 'privacy') {
                if (!context.mounted) {
                  return;
                }
                await openPrivacyPolicy(context, session.baseUrl);
                return;
              }
              if (value == 'logout') {
                final ok = await performGuardedLogout(context);
                if (!ok || !context.mounted) {
                  return;
                }
                if (!context.read<SessionProvider>().isAuthenticated) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const LoginPage()),
                    (_) => false,
                  );
                }
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'privacy',
                height: 38,
                child: ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  visualDensity: VisualDensity.compact,
                  leading: Icon(
                    Icons.policy_outlined,
                    size: 18,
                    color: AppColors.textMuted,
                  ),
                  title: Text(
                    'Confidentialit\u00e9',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                          fontSize: 13,
                        ),
                  ),
                ),
              ),
              const PopupMenuDivider(height: 4),
              const PopupMenuItem(
                value: 'logout',
                child: ListTile(
                  leading: Icon(Icons.logout),
                  title: Text('D\u00e9connexion'),
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // ── Bandeau utilisateur / role ─────────────────────────────────
          Material(
            color: AppColors.cardCream,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.person_outline,
                      size: 22, color: AppColors.ciGreenDark),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Connecte : ${_displayName(session)}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                    ),
                  ),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.navIndicator,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _rolePillLabel(session.user),
                      style: const TextStyle(
                        color: AppColors.ciGreenDark,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // ── Bandeau GPS refuse ────────────────────────────────────────
          if (!session.gpsGranted)
            Material(
              color: Colors.orange.shade50,
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                child: Row(
                  children: [
                    Icon(Icons.location_off,
                        color: Colors.orange.shade700, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'GPS non autoris\u00e9 \u2014 le scan et le suivi de '
                        'pr\u00e9sence ne fonctionneront pas.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.orange.shade900,
                        ),
                      ),
                    ),
                    TextButton(
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        foregroundColor: Colors.orange.shade800,
                      ),
                      onPressed: () => _requestGps(session),
                      child: const Text('Activer',
                          style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ),

          // ── Pages ─────────────────────────────────────────────────────
          Expanded(
            child: IndexedStack(
              index: _index,
              children: [
                ScanPage(isActive: _index == 0),
                const HistoryPage(),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (v) => setState(() => _index = v),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.qr_code_scanner_outlined),
            selectedIcon: Icon(Icons.qr_code_scanner),
            label: 'Scanner',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: 'Historique',
          ),
        ],
      ),
    );
  }
}
