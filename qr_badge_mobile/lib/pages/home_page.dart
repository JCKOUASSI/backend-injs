import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/guarded_logout.dart';
import '../utils/open_privacy_policy.dart';
import 'history_page.dart';
import 'home_dashboard_page.dart';
import 'login_page.dart';
import 'profile_fiche_page.dart';
import 'scan_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  int _index = 1;
  bool _ficheVisible = false;
  final _scaffoldKey = GlobalKey<ScaffoldState>();

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

  String get _title {
    switch (_index) {
      case 0:
        return 'Scanner';
      case 1:
        return 'Accueil';
      case 2:
        return 'Historique';
      default:
        return 'QR Badge';
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionProvider>();

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: AppColors.ciLight,
      drawer: _AppDrawer(
        onRequestGps: () => _requestGps(session),
        onOpenFiche: () => setState(() => _ficheVisible = true),
      ),
      appBar: _ficheVisible || _index == 0
          ? null
          : AppBar(
              centerTitle: _index == 2,
              title: Text(_title),
              leading: IconButton(
                icon: const Icon(Icons.menu),
                onPressed: () => _scaffoldKey.currentState?.openDrawer(),
              ),
              automaticallyImplyLeading: false,
              actions: [
                if (_index == 1)
                  IconButton(
                    icon: const Icon(Icons.notifications_outlined),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Aucune notification pour le moment.'),
                        ),
                      );
                    },
                  ),
              ],
            ),
      body: Stack(
        children: [
          Column(
        children: [
          if (!session.gpsGranted && _index != 0)
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
                        'GPS non autoris\u00e9 \u2014 le scan ne fonctionnera pas correctement.',
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
          Expanded(
            child: IndexedStack(
              index: _index,
              children: [
                ScanPage(
                  isActive: _index == 0,
                  onOpenMenu: () => _scaffoldKey.currentState?.openDrawer(),
                ),
                HomeDashboardPage(
                  onOpenHistory: () => setState(() => _index = 2),
                ),
                const HistoryPage(),
              ],
            ),
          ),
        ],
      ),
          Positioned.fill(
            child: IgnorePointer(
              ignoring: !_ficheVisible,
              child: Offstage(
                offstage: !_ficheVisible,
                child: ProfileFichePage(
                  onClose: () => setState(() => _ficheVisible = false),
                  onOpenHistory: () => setState(() {
                    _ficheVisible = false;
                    _index = 2;
                  }),
                ),
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: _ficheVisible
          ? null
          : NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (v) => setState(() => _index = v),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.qr_code_scanner_outlined),
            selectedIcon: Icon(Icons.qr_code_scanner),
            label: 'Scanner',
          ),
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Accueil',
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

class _AppDrawer extends StatelessWidget {
  const _AppDrawer({
    required this.onRequestGps,
    required this.onOpenFiche,
  });

  final VoidCallback onRequestGps;
  final VoidCallback onOpenFiche;

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionProvider>();
    return Drawer(
      child: SafeArea(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: AppColors.ciGreenDark),
              child: Align(
                alignment: Alignment.bottomLeft,
                child: Text(
                  'QR Badge',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.badge_outlined),
              title: const Text('Fiche'),
              onTap: () {
                Navigator.pop(context);
                onOpenFiche();
              },
            ),
            ListTile(
              leading: const Icon(Icons.location_on_outlined),
              title: const Text('Autoriser le GPS'),
              onTap: () {
                Navigator.pop(context);
                onRequestGps();
              },
            ),
            ListTile(
              leading: const Icon(Icons.policy_outlined),
              title: const Text('Confidentialité'),
              onTap: () async {
                Navigator.pop(context);
                await openPrivacyPolicy(context, session.baseUrl);
              },
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout, color: AppColors.ciDanger),
              title: const Text('Déconnexion'),
              onTap: () async {
                Navigator.pop(context);
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
              },
            ),
          ],
        ),
      ),
    );
  }
}
