import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/scan_service.dart';
import '../theme/qr_badge_theme.dart';
import '../widgets/home_summary_card.dart';
import '../widgets/qr_badge_logo.dart';

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

class HomeDashboardPage extends StatefulWidget {
  const HomeDashboardPage({super.key, this.onOpenHistory});

  final VoidCallback? onOpenHistory;

  @override
  State<HomeDashboardPage> createState() => _HomeDashboardPageState();
}

class _HomeDashboardPageState extends State<HomeDashboardPage>
    with AutomaticKeepAliveClientMixin {
  final _service = ScanService();
  bool _loading = true;
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
      setState(() => _loading = false);
      return;
    }
    setState(() => _loading = true);
    try {
      final res = await _service.myHistory(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        onRefreshToken: () => session.tryRefreshToken().then(
              (ok) => ok ? session.accessToken : null,
            ),
      );
      if (mounted) {
        setState(() => _payload = res);
      }
    } catch (_) {
      // Tableau de bord dégradé sans historique.
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  List<Map<String, dynamic>> _pointages() {
    final raw = _payload?['pointages'];
    if (raw is! List) {
      return [];
    }
    return raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Map<String, dynamic>? _dernierPointage(List<Map<String, dynamic>> items) {
    if (items.isEmpty) {
      return null;
    }
    final sorted = [...items];
    sorted.sort((a, b) {
      final ta = DateTime.tryParse(
            (a['timestamp_entree'] ?? a['timestamp_sortie'] ?? '').toString(),
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0);
      final tb = DateTime.tryParse(
            (b['timestamp_entree'] ?? b['timestamp_sortie'] ?? '').toString(),
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0);
      return tb.compareTo(ta);
    });
    return sorted.first;
  }

  int _ouvertsSansSortie(List<Map<String, dynamic>> items) {
    return items
        .where((m) =>
            m['timestamp_entree'] != null && m['timestamp_sortie'] == null)
        .length;
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final session = context.watch<SessionProvider>();
    final items = _pointages();
    final dernier = _dernierPointage(items);
    final aVerifier = _ouvertsSansSortie(items) +
        (session.gpsGranted ? 0 : 1) +
        (session.heartbeatGpsBlocked ? 1 : 0);
    final sansProbleme = items.length - _ouvertsSansSortie(items);
    final systemOk = session.gpsGranted && !session.heartbeatGpsBlocked;

    String dernierSousTitre = 'Aucun scan enregistré.';
    if (dernier != null) {
      final dt = DateTime.tryParse(
        (dernier['timestamp_entree'] ?? dernier['timestamp_sortie'] ?? '')
            .toString(),
      );
      if (dt != null) {
        final now = DateTime.now();
        final sameDay = dt.year == now.year &&
            dt.month == now.month &&
            dt.day == now.day;
        final prefix =
            sameDay ? 'Aujourd\'hui' : DateFormat('d MMMM', 'fr_FR').format(dt);
        dernierSousTitre =
            '$prefix à ${DateFormat.Hm('fr_FR').format(dt.toLocal())} / Aucun problème détecté.';
      }
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          Row(
            children: [
              const QrBadgeLogo(
                size: 52,
                color: AppColors.ciGreenDark,
                backgroundColor: AppColors.iconQrBg,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Bonjour, ${_displayName(session)} \u{1F44B}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Voici un résumé de votre activité.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (_loading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: CircularProgressIndicator()),
            )
          else ...[
            HomeSummaryCard(
              icon: Icons.verified_user,
              iconBg: AppColors.iconQrBg,
              iconColor: AppColors.ciGreenDark,
              title: 'Statut du système',
              subtitle: systemOk
                  ? 'Tout fonctionne correctement.'
                  : 'Vérifiez le GPS et la connexion.',
              trailing: StatusPill(
                label: systemOk ? 'Opérationnel' : 'À vérifier',
                color: systemOk ? AppColors.ciGreenDark : AppColors.ciOrangeDark,
                backgroundColor:
                    systemOk ? AppColors.navIndicator : AppColors.badgeOrangeBg,
                icon: systemOk ? Icons.check : Icons.warning_amber_rounded,
              ),
            ),
            HomeSummaryCard(
              icon: Icons.phonelink_lock,
              iconBg: AppColors.iconQrBg,
              iconColor: AppColors.ciGreenDark,
              title: 'Dernier scan',
              subtitle: dernierSousTitre,
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (dernier != null)
                    const StatusPill(
                      label: 'Aucun problème',
                      color: AppColors.ciGreenDark,
                      backgroundColor: AppColors.navIndicator,
                      icon: Icons.check,
                    ),
                  if (widget.onOpenHistory != null) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.chevron_right, color: AppColors.textSecondary.withValues(alpha: 0.6)),
                  ],
                ],
              ),
              onTap: widget.onOpenHistory,
            ),
            if (aVerifier > 0)
              HomeSummaryCard(
                icon: Icons.warning_amber_rounded,
                iconBg: AppColors.badgeOrangeBg,
                iconColor: AppColors.ciOrangeDark,
                title: 'Éléments à vérifier',
                subtitle:
                    '$aVerifier élément${aVerifier > 1 ? 's' : ''} nécessitent votre attention.',
                trailing: const StatusPill(
                  label: 'À vérifier',
                  color: AppColors.ciOrangeDark,
                  backgroundColor: AppColors.badgeOrangeBg,
                  icon: Icons.warning_amber_rounded,
                ),
                onTap: widget.onOpenHistory,
              ),
            _ResumeCard(
              scans: items.length,
              ok: sansProbleme.clamp(0, items.length),
              alertes: aVerifier,
            ),
          ],
        ],
      ),
    );
  }
}

class _ResumeCard extends StatelessWidget {
  const _ResumeCard({
    required this.scans,
    required this.ok,
    required this.alertes,
  });

  final int scans;
  final int ok;
  final int alertes;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderColor.withValues(alpha: 0.6)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Résumé',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 16),
          IntrinsicHeight(
            child: Row(
              children: [
                Expanded(
                  child: _ResumeCol(
                    icon: Icons.qr_code_scanner,
                    iconColor: AppColors.ciGreenDark,
                    value: '$scans',
                    valueColor: AppColors.ciGreenDark,
                    label: 'Scans réalisés',
                  ),
                ),
                VerticalDivider(color: AppColors.borderColor, width: 24),
                Expanded(
                  child: _ResumeCol(
                    icon: Icons.check_circle_outline,
                    iconColor: AppColors.ciGreenDark,
                    value: '$ok',
                    valueColor: AppColors.ciGreenDark,
                    label: 'Sans problème',
                  ),
                ),
                VerticalDivider(color: AppColors.borderColor, width: 24),
                Expanded(
                  child: _ResumeCol(
                    icon: Icons.warning_amber_rounded,
                    iconColor: AppColors.ciOrangeDark,
                    value: '$alertes',
                    valueColor: AppColors.ciOrangeDark,
                    label: 'À vérifier',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ResumeCol extends StatelessWidget {
  const _ResumeCol({
    required this.icon,
    required this.iconColor,
    required this.value,
    required this.valueColor,
    required this.label,
  });

  final IconData icon;
  final Color iconColor;
  final String value;
  final Color valueColor;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: iconColor, size: 22),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            color: valueColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: AppColors.textSecondary,
                height: 1.2,
              ),
        ),
      ],
    );
  }
}
