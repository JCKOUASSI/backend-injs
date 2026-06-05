import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_client.dart';
import '../services/scan_service.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/auth_navigation.dart';

class _HistoryEvent {
  _HistoryEvent({
    required this.at,
    required this.label,
    required this.success,
  });

  final DateTime at;
  final String label;
  final bool success;
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> with AutomaticKeepAliveClientMixin {
  final _service = ScanService();
  bool _loading = true;
  String? _error;
  List<_HistoryEvent> _events = [];
  int _lastRefreshTick = -1;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _maybeReloadFromTick(int tick) {
    if (tick == _lastRefreshTick) {
      return;
    }
    _lastRefreshTick = tick;
    _load();
  }

  List<_HistoryEvent> _eventsFromPayload(Map<String, dynamic>? p) {
    final rawList = p?['pointages'];
    final items = rawList is List ? rawList.cast<dynamic>() : <dynamic>[];
    final events = <_HistoryEvent>[];
    for (final raw in items) {
      final m = Map<String, dynamic>.from(raw as Map);
      final entree = DateTime.tryParse((m['timestamp_entree'] ?? '').toString());
      final sortie = DateTime.tryParse((m['timestamp_sortie'] ?? '').toString());
      final statut = (m['statut'] ?? '').toString();
      const okStatuts = {
        '', 'PRESENT', 'VALIDE', 'EN_COURS', 'TERMINE', 'FORCE_DFRC',
      };
      const alertStatuts = {
        'HORS_LIGNE_SUSPECT', 'ABSENT_NON_BADGE', 'SORTIE_AUTO',
      };
      final ok = okStatuts.contains(statut) && !alertStatuts.contains(statut);
      final titre = (m['formation_titre'] ?? '').toString().trim();
      final module = (m['module_intitule'] ?? '').toString().trim();
      final contexte = [titre, module].where((s) => s.isNotEmpty).join(' · ');
      if (entree != null) {
        events.add(_HistoryEvent(
          at: entree.toLocal(),
          label: contexte.isEmpty ? 'Entrée' : '$contexte — Entrée',
          success: ok,
        ));
      }
      if (sortie != null) {
        final sortieLabel = statut == 'SORTIE_AUTO'
            ? 'Sortie automatique'
            : 'Sortie';
        events.add(_HistoryEvent(
          at: sortie.toLocal(),
          label: contexte.isEmpty ? sortieLabel : '$contexte — $sortieLabel',
          success: ok,
        ));
      }
    }
    events.sort((a, b) => b.at.compareTo(a.at));
    return events;
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
      setState(() => _events = _eventsFromPayload(res));
    } on SessionExpiredException {
      if (mounted) {
        await context.read<SessionProvider>().logout();
        if (!mounted) return;
        resetToAuthRoot(context);
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

  @override
  Widget build(BuildContext context) {
    super.build(context);
    _maybeReloadFromTick(context.watch<SessionProvider>().historyRefreshTick);
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

    if (_events.isEmpty) {
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

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        itemCount: _events.length,
        separatorBuilder: (context, index) => const SizedBox(height: 10),
        itemBuilder: (context, i) => _HistoryEntryCard(event: _events[i]),
      ),
    );
  }
}

class _HistoryEntryCard extends StatelessWidget {
  const _HistoryEntryCard({required this.event});

  final _HistoryEvent event;

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('d MMMM yyyy', 'fr_FR');
    final timeFmt = DateFormat.Hm('fr_FR');
    return Material(
      color: AppColors.cardBg,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.borderColor.withValues(alpha: 0.7)),
          boxShadow: const [
            BoxShadow(
              color: Color(0x08000000),
              blurRadius: 6,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: const BoxDecoration(
                color: AppColors.iconQrBg,
                shape: BoxShape.circle,
              ),
              child: Icon(
                event.success ? Icons.check : Icons.info_outline,
                color: event.success ? AppColors.ciGreenDark : AppColors.ciOrange,
                size: 24,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    dateFmt.format(event.at),
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    timeFmt.format(event.at),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    event.label,
                    style: TextStyle(
                      color: event.success
                          ? AppColors.ciGreenDark
                          : AppColors.ciOrangeDark,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
