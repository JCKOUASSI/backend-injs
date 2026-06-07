import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../providers/session_provider.dart';
import '../services/api_client.dart';
import '../services/profile_service.dart';
import '../theme/qr_badge_theme.dart';
import '../utils/auth_navigation.dart';
import '../widgets/home_summary_card.dart';
import '../widgets/qr_badge_logo.dart';

class ProfileFichePage extends StatefulWidget {
  const ProfileFichePage({super.key, this.onClose, this.onOpenHistory});

  /// Fermeture sans détruire l’état (overlay dans [HomePage]).
  final VoidCallback? onClose;
  final VoidCallback? onOpenHistory;

  @override
  State<ProfileFichePage> createState() => _ProfileFichePageState();
}

class _ProfileFichePageState extends State<ProfileFichePage> {
  final _service = ProfileService();
  final _scrollCtrl = ScrollController();
  final _modulesSectionKey = GlobalKey();
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _payload;
  int _lastRefreshTick = -1;

  @override
  void dispose() {
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollToModules() {
    final ctx = _modulesSectionKey.currentContext;
    if (ctx != null) {
      Scrollable.ensureVisible(
        ctx,
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeOutCubic,
      );
    }
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _close() {
    if (widget.onClose != null) {
      widget.onClose!();
    } else if (mounted) {
      Navigator.of(context).pop();
    }
  }

  Future<void> _load({bool showSpinner = true}) async {
    final session = context.read<SessionProvider>();
    if (session.accessToken == null) {
      setState(() {
        _error = 'Non connecté.';
        _loading = false;
      });
      return;
    }
    final firstLoad = _payload == null;
    setState(() {
      if (showSpinner && firstLoad) {
        _loading = true;
      }
      _error = null;
    });
    try {
      final res = await _service.myFiche(
        baseUrl: session.baseUrl,
        accessToken: session.accessToken!,
        onRefreshToken: () => session.tryRefreshToken().then(
              (ok) => ok ? session.accessToken : null,
            ),
      );
      setState(() => _payload = res);
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

  String _roleLabel(String? role) {
    switch (role) {
      case 'AUDITEUR':
        return 'Participant';
      case 'ENCADRANT':
        return 'Encadrant';
      case 'FORMATEUR':
        return 'Formateur';
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
        return role ?? '—';
    }
  }

  String _typeLabel(String? type) {
    switch (type) {
      case 'participant':
        return 'Auditeur';
      case 'formateur':
        return 'Formateur';
      case 'encadrant':
        return 'Encadrant';
      default:
        return type ?? '—';
    }
  }

  String _statutModuleLabel(String? statut) {
    switch (statut) {
      case 'EN_COURS':
        return 'En cours';
      case 'PLANIFIEE':
        return 'Planifiée';
      case 'SUSPENDUE':
        return 'Suspendue';
      case 'TERMINEE':
        return 'Terminée';
      default:
        return statut ?? '—';
    }
  }

  void _maybeReloadFromTick(int tick) {
    if (tick == _lastRefreshTick) {
      return;
    }
    _lastRefreshTick = tick;
    _load(showSpinner: false);
  }

  @override
  Widget build(BuildContext context) {
    _maybeReloadFromTick(context.watch<SessionProvider>().historyRefreshTick);
    final isFallback = _payload?['_fallback'] == true;

    return PopScope(
      canPop: widget.onClose == null,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) {
          _close();
        }
      },
      child: Scaffold(
      backgroundColor: AppColors.ciLight,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _close,
        ),
        title: const Text('Fiche'),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (isFallback)
            Material(
              color: Colors.orange.shade50,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                child: Text(
                  'Mode dégradé : redémarrez le serveur Django pour activer '
                  'l\u2019endpoint /api/me/fiche/.',
                  style: TextStyle(fontSize: 12, color: Colors.orange.shade900),
                ),
              ),
            ),
          Expanded(child: _buildBody(context)),
        ],
      ),
    ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Réessayer')),
            ],
          ),
        ),
      );
    }

    final user = Map<String, dynamic>.from(_payload?['utilisateur'] as Map? ?? {});
    final profil = Map<String, dynamic>.from(_payload?['profil'] as Map? ?? {});
    final stats = Map<String, dynamic>.from(_payload?['stats'] as Map? ?? {});
    final rawModules = _payload?['modules'];
    final modules = rawModules is List
        ? rawModules.map((e) => Map<String, dynamic>.from(e as Map)).toList()
        : <Map<String, dynamic>>[];

    final prenom = (profil['prenom'] ?? user['first_name'] ?? '').toString().trim();
    final nom = (profil['nom'] ?? user['last_name'] ?? '').toString().trim();
    final fullName = '$prenom $nom'.trim();
    final displayName =
        fullName.isNotEmpty ? fullName : user['username']?.toString() ?? '—';

    final dernierRaw = stats['dernier_badgeage']?.toString();
    final dernierDt = DateTime.tryParse(dernierRaw ?? '');
    final dernierLabel = dernierDt != null
        ? DateFormat('d MMMM yyyy à HH:mm', 'fr_FR').format(dernierDt.toLocal())
        : 'Aucun badgeage enregistré';

    final totalMin = stats['total_minutes_presence'];
    final minutesLabel = totalMin is num
        ? '${totalMin.round()} min de présence'
        : '0 min de présence';

    final volumeTotalRaw = stats['volume_horaire_total_heures'];
    final volumeTotal =
        volumeTotalRaw is num ? volumeTotalRaw.toDouble() : 0.0;
    final volumeEffectueRaw = stats['volume_horaire_effectue_heures'];
    final volumeEffectue = volumeEffectueRaw is num
        ? (volumeTotal > 0
            ? volumeEffectueRaw.toDouble().clamp(0.0, volumeTotal)
            : volumeEffectueRaw.toDouble())
        : 0.0;
    final volumeTauxRaw = stats['volume_horaire_effectue_taux'];
    final volumeTaux =
        volumeTauxRaw is num ? volumeTauxRaw.toDouble().clamp(0.0, 100.0) : 0.0;
    final volumeLabel =
        '${_formatHeures(volumeEffectue)} / ${_formatHeures(volumeTotal)}';

    final infoRows = _infoRowsFor(user, profil);

    return RefreshIndicator(
      onRefresh: () => _load(showSpinner: false),
      child: ListView(
        key: const PageStorageKey<String>('profile_fiche_scroll'),
        controller: _scrollCtrl,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          _FicheTappableCard(
            onTap: () => _showProfileSheet(
              context,
              displayName: displayName,
              user: user,
              profil: profil,
            ),
            child: Row(
              children: [
                const QrBadgeLogo(
                  size: 64,
                  color: AppColors.ciGreenDark,
                  backgroundColor: AppColors.iconQrBg,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        displayName,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _typeLabel(profil['type_personne']?.toString()),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                      ),
                      const SizedBox(height: 8),
                      StatusPill(
                        label: _roleLabel(user['role']?.toString()),
                        color: AppColors.ciGreenDark,
                        backgroundColor: AppColors.navIndicator,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          _SectionTitle(title: 'Informations'),
          _InfoCard(
            onTap: () => _showInfoSheet(context, rows: infoRows),
            rows: infoRows,
          ),
          if (profil['type_personne']?.toString() == 'formateur') ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _showBankingEditSheet(context, profil),
              icon: const Icon(Icons.account_balance_outlined, size: 18),
              label: const Text('Modifier pièce d\'identité / compte bancaire'),
            ),
          ],
          const SizedBox(height: 20),
          _SectionTitle(title: 'Statistiques personnelles'),
          _StatsGrid(
            stats: stats,
            volumeLabel: volumeLabel,
            volumeTaux: volumeTaux is num ? volumeTaux.toDouble() : 0,
            minutesLabel: minutesLabel,
            dernierLabel: dernierLabel,
            onVolumeTap: () => _showStatSheet(
              context,
              title: 'Volume horaire',
              value: volumeLabel,
              description:
                  'Heures de présence badgeées sur le volume total prévu de vos modules inscrits.'
                  '${volumeTaux is num && volumeTotal is num && volumeTotal > 0 ? ' (${volumeTaux.toStringAsFixed(volumeTaux == volumeTaux.roundToDouble() ? 0 : 1)} %).' : ''}',
            ),
            onBadgeagesTap: widget.onOpenHistory ?? () => _showStatSheet(
                      context,
                      title: 'Badgeages',
                      value: stats['nb_badgeages']?.toString() ?? '0',
                      description:
                          'Nombre total de pointages enregistrés sur votre compte.',
                    ),
            onTermineesTap: () => _showStatSheet(
              context,
              title: 'Séances terminées',
              value: stats['nb_seances_terminees']?.toString() ?? '0',
              description:
                  'Séances pour lesquelles une entrée et une sortie ont été enregistrées.',
            ),
            onModulesTap: modules.isEmpty ? null : _scrollToModules,
            onAVerifierTap: () => _showStatSheet(
              context,
              title: 'Éléments à vérifier',
              value: stats['nb_a_verifier']?.toString() ?? '0',
              description:
                  'Pointages en cours, sorties manquantes ou statuts nécessitant une attention.',
            ),
            onPresenceTap: () => _showStatSheet(
              context,
              title: 'Temps de présence',
              value: minutesLabel,
              description: 'Dernier badgeage : $dernierLabel',
            ),
          ),
          const SizedBox(height: 20),
          _SectionTitle(
            key: _modulesSectionKey,
            title: 'Modules inscrits',
            trailing: '${modules.length}',
          ),
          if (modules.isEmpty)
            _FicheTappableCard(
              onTap: null,
              padding: const EdgeInsets.all(20),
              child: Text(
                profil['type_personne'] == 'encadrant'
                    ? 'Aucun module d\u2019inscription pour un compte encadrant.'
                    : 'Aucun module inscrit pour le moment.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            )
          else
            ...modules.map(
              (m) => _ModuleCard(
                data: m,
                statut: _statutModuleLabel(m['statut']?.toString()),
                onTap: () => _showModuleSheet(context, m),
              ),
            ),
        ],
      ),
    );
  }

  List<_InfoRow> _infoRowsFor(
    Map<String, dynamic> user,
    Map<String, dynamic> profil,
  ) =>
      [
        _InfoRow('Identifiant', user['username']?.toString()),
        _InfoRow('Matricule / n°', profil['numero']?.toString()),
        _InfoRow('E-mail', user['email']?.toString()),
        _InfoRow('Téléphone', user['telephone']?.toString()),
        _InfoRow('Organisation', user['organisation']?.toString()),
        _InfoRow('Grade', user['grade']?.toString()),
        if (profil['specialite'] != null &&
            profil['specialite'].toString().isNotEmpty)
          _InfoRow('Spécialité', profil['specialite']?.toString()),
        if (profil['type_personne']?.toString() == 'formateur') ...[
          _InfoRow(
            'N° pièce d\'identité',
            profil['numero_piece_identite']?.toString(),
          ),
          _InfoRow(
            'N° compte bancaire',
            profil['numero_compte_bancaire']?.toString(),
          ),
        ],
        _InfoRow('Secrétariat', user['secretariat_nom']?.toString()),
      ];

  void _showProfileSheet(
    BuildContext context, {
    required String displayName,
    required Map<String, dynamic> user,
    required Map<String, dynamic> profil,
  }) {
    _showDetailSheet(
      context,
      title: displayName,
      children: [
        _DetailRow('Type', _typeLabel(profil['type_personne']?.toString())),
        _DetailRow('Rôle', _roleLabel(user['role']?.toString())),
        _DetailRow('Identifiant', user['username']?.toString()),
        _DetailRow('Matricule', profil['numero']?.toString()),
      ],
    );
  }

  void _showInfoSheet(BuildContext context, {required List<_InfoRow> rows}) {
    _showDetailSheet(
      context,
      title: 'Informations',
      children: rows
          .where((r) => r.value != null && r.value!.trim().isNotEmpty)
          .map((r) => _DetailRow(r.label, r.value))
          .toList(),
    );
  }

  Future<void> _showBankingEditSheet(
    BuildContext context,
    Map<String, dynamic> profil,
  ) async {
    final pieceCtrl = TextEditingController(
      text: profil['numero_piece_identite']?.toString() ?? '',
    );
    final compteCtrl = TextEditingController(
      text: profil['numero_compte_bancaire']?.toString() ?? '',
    );
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.cardBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        var saving = false;
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Informations bancaires',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: pieceCtrl,
                    decoration: const InputDecoration(
                      labelText: 'N° pièce d\'identité',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: compteCtrl,
                    decoration: const InputDecoration(
                      labelText: 'N° compte bancaire',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: saving
                        ? null
                        : () async {
                            setModalState(() => saving = true);
                            final session = context.read<SessionProvider>();
                            try {
                              await _service.updateMySensitiveData(
                                baseUrl: session.baseUrl,
                                accessToken: session.accessToken!,
                                numeroPieceIdentite: pieceCtrl.text.trim(),
                                numeroCompteBancaire: compteCtrl.text.trim(),
                                onRefreshToken: () => session
                                    .tryRefreshToken()
                                    .then((ok) => ok ? session.accessToken : null),
                              );
                              if (context.mounted) {
                                Navigator.of(context).pop(true);
                              }
                            } catch (e) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      e.toString().replaceFirst('Exception: ', ''),
                                    ),
                                  ),
                                );
                              }
                            } finally {
                              if (context.mounted) {
                                setModalState(() => saving = false);
                              }
                            }
                          },
                    child: Text(saving ? 'Enregistrement…' : 'Enregistrer'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
    pieceCtrl.dispose();
    compteCtrl.dispose();
    if (saved == true && mounted) {
      await _load(showSpinner: false);
    }
  }

  void _showStatSheet(
    BuildContext context, {
    required String title,
    required String value,
    required String description,
  }) {
    _showDetailSheet(
      context,
      title: title,
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.w700,
                color: AppColors.ciGreenDark,
              ),
        ),
        const SizedBox(height: 12),
        Text(
          description,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
        ),
      ],
    );
  }

  void _showModuleSheet(BuildContext context, Map<String, dynamic> m) {
    final statut = _statutModuleLabel(m['statut']?.toString());
    _showDetailSheet(
      context,
      title: m['module']?.toString() ?? 'Module',
      children: [
        if ((m['formation']?.toString() ?? '').isNotEmpty)
          _DetailRow('Formation', m['formation']?.toString()),
        _DetailRow('Statut', statut),
        _DetailRow('Grade', m['grade']?.toString()),
        _DetailRow('Groupe', m['groupe']?.toString()),
        _DetailRow('Vague', m['vague']?.toString()),
        _DetailRow('Site', m['site']?.toString()),
        _DetailRow('Début', m['date_debut']?.toString()),
        _DetailRow('Fin', m['date_fin']?.toString()),
        _DetailRow('Secrétariat', m['secretariat_nom']?.toString()),
        _DetailRow('Inscription', m['inscrit_le']?.toString()),
      ],
    );
  }

  void _showDetailSheet(
    BuildContext context, {
    required String title,
    required List<Widget> children,
  }) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.cardBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          12,
          20,
          20 + MediaQuery.paddingOf(ctx).bottom,
        ),
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
            Text(
              title,
              style: Theme.of(ctx).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _FicheTappableCard extends StatelessWidget {
  const _FicheTappableCard({
    required this.onTap,
    required this.child,
    this.padding = const EdgeInsets.all(18),
  });

  final VoidCallback? onTap;
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.cardBg,
      borderRadius: BorderRadius.circular(14),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: AppColors.borderColor.withValues(alpha: 0.6),
            ),
          ),
          child: Row(
            children: [
              Expanded(child: child),
              if (onTap != null)
                Icon(
                  Icons.chevron_right,
                  color: AppColors.textSecondary.withValues(alpha: 0.5),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow(this.label, this.value);

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    if (value == null || value!.trim().isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({super.key, required this.title, this.trailing});

  final String title;
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ),
          if (trailing != null)
            Text(
              trailing!,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: AppColors.ciGreenDark,
                    fontWeight: FontWeight.w600,
                  ),
            ),
        ],
      ),
    );
  }
}

class _InfoRow {
  const _InfoRow(this.label, this.value);
  final String label;
  final String? value;
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.rows, this.onTap});

  final List<_InfoRow> rows;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final visible = rows
        .where((r) => r.value != null && r.value!.trim().isNotEmpty)
        .toList();
    if (visible.isEmpty) {
      return const SizedBox.shrink();
    }
    return _FicheTappableCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        children: visible
            .map(
              (r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 110,
                      child: Text(
                        r.label,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                              fontWeight: FontWeight.w500,
                            ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        r.value!,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

String _formatHeures(dynamic h) {
  if (h is! num) return '0 h';
  final v = h.toDouble();
  if (v == v.roundToDouble()) return '${v.round()} h';
  return '${v.toStringAsFixed(1)} h';
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({
    required this.stats,
    required this.volumeLabel,
    required this.volumeTaux,
    required this.minutesLabel,
    required this.dernierLabel,
    this.onVolumeTap,
    this.onBadgeagesTap,
    this.onTermineesTap,
    this.onModulesTap,
    this.onAVerifierTap,
    this.onPresenceTap,
  });

  final Map<String, dynamic> stats;
  final String volumeLabel;
  final double volumeTaux;
  final String minutesLabel;
  final String dernierLabel;
  final VoidCallback? onVolumeTap;
  final VoidCallback? onBadgeagesTap;
  final VoidCallback? onTermineesTap;
  final VoidCallback? onModulesTap;
  final VoidCallback? onAVerifierTap;
  final VoidCallback? onPresenceTap;

  String _n(String key) => stats[key]?.toString() ?? '0';

  @override
  Widget build(BuildContext context) {
    final progress = (volumeTaux / 100).clamp(0.0, 1.0);
    final tauxDisplay = volumeTaux == volumeTaux.roundToDouble()
        ? '${volumeTaux.round()} %'
        : '${volumeTaux.toStringAsFixed(1)} %';

    return Column(
      children: [
        _FicheTappableCard(
          onTap: onVolumeTap,
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.schedule, size: 20, color: AppColors.ciGreenDark),
                  const SizedBox(width: 8),
                  Text(
                    'Volume horaire',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.textSecondary,
                        ),
                  ),
                  const Spacer(),
                  Text(
                    tauxDisplay,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColors.ciGreenDark,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                volumeLabel,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.ciGreenDark,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                'Effectué / total prévu',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress > 0 ? progress : null,
                  minHeight: 6,
                  backgroundColor: AppColors.navIndicator,
                  color: AppColors.ciGreenDark,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _StatTile(
                icon: Icons.qr_code_scanner,
                value: _n('nb_badgeages'),
                label: 'Badgeages',
                color: AppColors.ciGreenDark,
                onTap: onBadgeagesTap,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatTile(
                icon: Icons.check_circle_outline,
                value: _n('nb_seances_terminees'),
                label: 'Séances terminées',
                color: AppColors.ciGreenDark,
                onTap: onTermineesTap,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _StatTile(
                icon: Icons.menu_book_outlined,
                value: _n('nb_modules_inscrits'),
                label: 'Modules inscrits',
                color: AppColors.ciBlue,
                onTap: onModulesTap,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatTile(
                icon: Icons.warning_amber_rounded,
                value: _n('nb_a_verifier'),
                label: 'À vérifier',
                color: AppColors.ciOrangeDark,
                onTap: onAVerifierTap,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _FicheTappableCard(
          onTap: onPresenceTap,
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                minutesLabel,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.ciGreenDark,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                'Dernier badgeage : $dernierLabel',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
    this.onTap,
  });

  final IconData icon;
  final String value;
  final String label;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return _FicheTappableCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      child: Column(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: color,
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
      ),
    );
  }
}

class _ModuleCard extends StatelessWidget {
  const _ModuleCard({
    required this.data,
    required this.statut,
    required this.onTap,
  });

  final Map<String, dynamic> data;
  final String statut;
  final VoidCallback onTap;

  String? _fmtDate(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    final d = DateTime.tryParse(raw.length >= 10 ? raw.substring(0, 10) : raw);
    if (d == null) return raw;
    return DateFormat('d MMM yyyy', 'fr_FR').format(d);
  }

  @override
  Widget build(BuildContext context) {
    final formation = data['formation']?.toString() ?? '';
    final module = data['module']?.toString() ?? 'Module';
    final grade = data['grade']?.toString();
    final groupe = data['groupe']?.toString();
    final vague = data['vague']?.toString();
    final site = data['site']?.toString();
    final dateDebut = data['date_debut']?.toString();
    final dateFin = data['date_fin']?.toString();
    final secretariat = data['secretariat_nom']?.toString();
    final inscritLe = data['inscrit_le']?.toString();

    final periode = [
      if (_fmtDate(dateDebut) != null) 'Du ${_fmtDate(dateDebut)}',
      if (_fmtDate(dateFin) != null) 'au ${_fmtDate(dateFin)}',
    ].join(' ');

    final meta = [
      if (grade != null && grade.isNotEmpty) 'Grade $grade',
      if (groupe != null && groupe.isNotEmpty) 'Groupe $groupe',
      if (vague != null && vague.isNotEmpty) 'Vague $vague',
      if (site != null && site.isNotEmpty) site,
    ].join(' · ');

    final inscritDt = DateTime.tryParse(inscritLe ?? '');
    final inscritLabel = inscritDt != null
        ? 'Inscrit le ${DateFormat('d MMM yyyy', 'fr_FR').format(inscritDt.toLocal())}'
        : null;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _FicheTappableCard(
        onTap: onTap,
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (formation.isNotEmpty)
                        Text(
                          formation,
                          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                color: AppColors.ciGreenDark,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      const SizedBox(height: 4),
                      Text(
                        module,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ],
                  ),
                ),
                StatusPill(
                  label: statut,
                  color: AppColors.ciGreenDark,
                  backgroundColor: AppColors.navIndicator,
                ),
              ],
            ),
            if (meta.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                meta,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
            if (periode.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                periode,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
            if (secretariat != null && secretariat.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                secretariat,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ],
            if (inscritLabel != null) ...[
              const SizedBox(height: 6),
              Text(
                inscritLabel,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppColors.textMuted,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
