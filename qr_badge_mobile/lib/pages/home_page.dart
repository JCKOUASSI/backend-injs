import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/guarded_logout.dart';
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
      return 'Secrétariat';
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
  return session.user?['username']?.toString() ?? session.username ?? '—';
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _index = 0;

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
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'logout', child: Text('Déconnexion')),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          Material(
            color: AppColors.cardCream,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.person_outline, size: 22, color: AppColors.ciGreenDark),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Connecté : ${_displayName(session)}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.navIndicator,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _rolePillLabel(session.user),
                      style: TextStyle(
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
