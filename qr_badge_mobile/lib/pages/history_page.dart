import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_client.dart';
import '../services/scan_service.dart';
import '../theme/qr_badge_theme.dart';
import 'login_page.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> with AutomaticKeepAliveClientMixin {
  final _service = ScanService();
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _payload;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final session = context.read<SessionProvider>();
    if (session.accessToken == null) {
      setState(() {
        _error = 'Non connecté.';
        _loading = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await _service.myHistory(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        onRefreshToken: () => session.tryRefreshToken().then(
              (ok) => ok ? session.accessToken : null,
            ),
      );
      setState(() => _payload = res);
    } on SessionExpiredException {
      // Refresh token expiré — déconnecter et renvoyer vers le login.
      if (mounted) {
        await context.read<SessionProvider>().logout();
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const LoginPage()),
          (_) => false,
        );
      }
      return;
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  String _fullName(Map<String, dynamic>? p, SessionProvider session) {
    if (p != null) {
      final prenom = (p['prenom'] ?? '').toString().trim();
      final nom = (p['nom'] ?? '').toString().trim();
      final s = '$prenom $nom'.trim();
      if (s.isNotEmpty) {
        return s;
      }
    }
    final u = session.user;
    if (u != null) {
      final fn = (u['first_name'] ?? '').toString().trim();
      final ln = (u['last_name'] ?? '').toString().trim();
      final full = '$fn $ln'.trim();
      if (full.isNotEmpty) {
        return full;
      }
    }
    return session.username ?? '—';
  }

  String? _numeroMatricule(Map<String, dynamic>? p) {
    if (p == null) {
      return null;
    }
    final n = p['numero']?.toString().trim();
    if (n != null && n.isNotEmpty) {
      return n;
    }
    return null;
  }

  int _minutes(dynamic v) {
    if (v == null) {
      return 0;
    }
    if (v is num) {
      return v.round();
    }
    return double.tryParse(v.toString())?.round() ?? 0;
  }

  String _hm(dynamic raw) {
    if (raw == null) {
      return '—';
    }
    final dt = DateTime.tryParse(raw.toString());
    if (dt == null) {
      return '—';
    }
    return DateFormat.Hm('fr_FR').format(dt.toLocal());
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              const SizedBox(height: 8),
              OutlinedButton(onPressed: _load, child: const Text('Réessayer')),
            ],
          ),
        ),
      );
    }

    final p = _payload;
    final rawList = p?['pointages'];
    final items = rawList is List ? rawList.cast<dynamic>() : <dynamic>[];

    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Aucun historique disponible.'),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: _load, child: const Text('Rafraîchir')),
          ],
        ),
      );
    }

    final session = context.watch<SessionProvider>();
    final rows = items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    final byDay = <String, List<Map<String, dynamic>>>{};
    for (final m in rows) {
      final k = (m['date_journee'] ?? '').toString();
      if (k.isEmpty) {
        continue;
      }
      byDay.putIfAbsent(k, () => []).add(m);
    }
    final dayKeys = byDay.keys.toList()..sort((a, b) => b.compareTo(a));

    final nb = items.length;
    final displayName = _fullName(p, session);
    final numero = _numeroMatricule(p);

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.cardCream,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                const Icon(Icons.person, color: AppColors.ciGreenDark, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        displayName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      if (numero != null)
                        Text(
                          numero,
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: AppColors.textMuted,
                              ),
                        ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.badgeOrangeBg,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '$nb badgeage${nb > 1 ? 's' : ''}',
                    style: const TextStyle(
                      color: AppColors.badgeOrangeFg,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ...dayKeys.expand((dayKey) {
            final dayItems = byDay[dayKey] ?? [];
            final dateLabel = _dayHeaderLabel(dayKey);
            final totalMin = dayItems.fold<int>(0, (s, m) => s + _minutes(m['duree_presence_minutes']));
            return [
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        dateLabel,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                    ),
                    Text(
                      '$totalMin min',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: AppColors.badgeOrangeFg,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ],
                ),
              ),
              ...dayItems.map((m) => _SessionCard(
                    titre: m['formation_titre']?.toString() ?? 'Formation',
                    entree: _hm(m['timestamp_entree']),
                    sortie: _hm(m['timestamp_sortie']),
                    minutes: _minutes(m['duree_presence_minutes']),
                  )),
              const SizedBox(height: 12),
            ];
          }),
        ],
      ),
    );
  }

  String _dayHeaderLabel(String dayKey) {
    final d = DateTime.tryParse(dayKey.length >= 10 ? dayKey.substring(0, 10) : dayKey);
    if (d == null) {
      return dayKey;
    }
    return DateFormat.yMMMMEEEEd('fr_FR').format(d);
  }
}

class _SessionCard extends StatelessWidget {
  const _SessionCard({
    required this.titre,
    required this.entree,
    required this.sortie,
    required this.minutes,
  });

  final String titre;
  final String entree;
  final String sortie;
  final int minutes;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: AppColors.cardGrey,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.iconQrBg,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.check_circle, color: AppColors.ciGreen, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      titre,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '-> $entree    <- $sortie',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.textMuted,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.badgeOrangeBg,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '$minutes min',
                  style: const TextStyle(
                    color: AppColors.badgeOrangeFg,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
