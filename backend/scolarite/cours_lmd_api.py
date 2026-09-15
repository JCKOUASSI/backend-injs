"""Lot B — vue « Enseignement / Cours » du modèle fonctionnel 04 (chaîne
ANNEE → FORMATION → PARCOURS → NIVEAU → SEMESTRE → UE → ECUE → ENSEIGNEMENT →
GROUPE → SÉANCE).

``AffectationPedagogique`` EST la ligne de cours du modèle ; cette API la joint
au planning EDT (``edts.AffectationCreneau`` via groupe + cycle), à l'effectif
du groupe (affectations de groupe actives) et à l'avancement des présences
(pointages de séances LMD du lot C) — lecture seule, aucune donnée dupliquée.

Route : ``GET /api/scolarite/pedagogie/cours/`` (authentifié ; portée legacy).
Filtres : annee, ref_formation, niveau, semestre, groupe, enseignant, statut,
type_enseignement, q (recherche ECUE / enseignant / groupe).
"""
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from edts.models import AffectationCreneau
from presences.models import Pointage
from scolarite.models import AffectationGroupe, AffectationPedagogique, AnneeAcademique

_STATUTS_HORS_CADRE = ('ANNULEE',)


def _int(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cours_list(request):
    p = request.query_params
    qs = (AffectationPedagogique.objects
          .select_related('annee_academique', 'ref_formation', 'parcours', 'niveau',
                          'semestre', 'ue', 'ecue', 'groupe', 'enseignant')
          .exclude(statut__in=_STATUTS_HORS_CADRE))

    annee = _int(p.get('annee'))
    if annee is None and not p.get('annee') and p.get('annee') != '':
        courante = AnneeAcademique.objects.filter(courante=True).first()
        annee = courante.pk if courante else None
    if annee is not None:
        qs = qs.filter(annee_academique_id=annee)
    for champ in ('ref_formation', 'niveau', 'semestre', 'groupe', 'enseignant'):
        val = _int(p.get(champ))
        if val is not None:
            qs = qs.filter(**{f'{champ}_id': val})
    statut = (p.get('statut') or '').strip().upper()
    if statut:
        qs = qs.filter(statut=statut)
    typ = (p.get('type_enseignement') or '').strip().upper()
    if typ:
        qs = qs.filter(type_enseignement=typ)
    q = (p.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(ecue__code__icontains=q) | Q(ecue__intitule__icontains=q)
                       | Q(enseignant__nom__icontains=q) | Q(enseignant__prenom__icontains=q)
                       | Q(groupe__nom__icontains=q) | Q(semestre__libelle__icontains=q))

    affectations = list(qs.order_by('-annee_academique__libelle', 'semestre__numero',
                                    'ecue__code', 'groupe__nom')[:500])

    # Plans de séance EDT : mêmes clés (groupe, cycle) que l'affectation.
    groupe_ids = {a.groupe_id for a in affectations if a.groupe_id}
    cycle_ids = {a.ref_formation_id for a in affectations if a.ref_formation_id}
    creneaux_par_groupe = {}
    seances_ids_par_groupe = {}
    if groupe_ids:
        creneaux = (AffectationCreneau.objects
                    .filter(groupe_id__in=groupe_ids, actif=True,
                            emploi_du_temps__statut__in=('VALIDE', 'PUBLIE'))
                    .select_related('creneau_template', 'emploi_du_temps__annee_academique'))
        if cycle_ids:
            creneaux = creneaux.filter(Q(formation_id__in=cycle_ids) | Q(formation__isnull=True))
        for creneau in creneaux:
            entree = creneaux_par_groupe.setdefault(creneau.groupe_id, [])
            entree.append(creneau)
            seances_ids_par_groupe.setdefault(creneau.groupe_id, set()).add(creneau.pk)

    effectifs = dict(
        AffectationGroupe.objects.filter(active=True, groupe_id__in=groupe_ids or [-1])
        .values_list('groupe_id')
        .annotate(n=Count('id'))
    ) if groupe_ids else {}

    nb_seances_realisees = {}
    if groupe_ids:
        tous_ids = [i for ids in seances_ids_par_groupe.values() for i in ids]
        if tous_ids:
            compte = (Pointage.objects
                      .filter(seance_edt_id__in=tous_ids)
                      .values('seance_edt_id')
                      .annotate(jours=Count('date_journee', distinct=True)))
            par_creneau = {r['seance_edt_id']: r['jours'] for r in compte}
            for gid, ids in seances_ids_par_groupe.items():
                nb_seances_realisees[gid] = max((par_creneau.get(i, 0) for i in ids), default=0)

    JOURS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    lignes = []
    for a in affectations:
        creneaux = creneaux_par_groupe.get(a.groupe_id, []) if a.groupe_id else []
        planning = []
        semaines = 0
        for creneau in sorted(creneaux, key=lambda c: (c.creneau_template.jour,
                                                       c.creneau_template.heure_debut)):
            ct = creneau.creneau_template
            semaine_debut = creneau.semaine_debut
            semaine_fin = creneau.semaine_fin
            semaines = max(semaines, semaine_fin - semaine_debut + 1)
            salle = creneau.salle_nom or ''
            planning.append({
                'id': creneau.pk,
                'jour': ct.jour.capitalize(),
                'horaire': f'{ct.heure_debut:%H:%M}–{ct.heure_fin:%H:%M}',
                'salle': salle,
                'semaines': f'S{semaine_debut}–S{semaine_fin}',
                'nature': creneau.get_nature_display(),
            })
        lignes.append({
            'id': a.pk,
            'annee': a.annee_academique.libelle if a.annee_academique_id else '',
            'ref_formation': a.ref_formation_id,
            'cycle': a.ref_formation.intitule if a.ref_formation_id else '',
            'parcours': getattr(a.parcours, 'libelle', '') if a.parcours_id else '',
            'niveau': a.niveau.libelle if a.niveau_id else '',
            'semestre': (a.semestre.libelle or f'S{a.semestre.numero}') if a.semestre_id else '',
            'ue': getattr(a.ue, 'libelle', '') or getattr(a.ue, 'code', '') if a.ue_id else '',
            'ecue': a.ecue.code if a.ecue_id else '',
            'ecue_intitule': a.ecue.intitule if a.ecue_id else '',
            'credits': a.ecue.credits if a.ecue_id else None,
            'type_enseignement': a.type_enseignement,
            'volume_horaire': float(a.volume_horaire or 0),
            'groupe': a.groupe_id,
            'groupe_nom': a.groupe.nom if a.groupe_id else '',
            'effectif': effectifs.get(a.groupe_id, 0) if a.groupe_id else None,
            'capacite_max': a.groupe.capacite_max if a.groupe_id else None,
            'enseignant': (f'{a.enseignant.nom} {a.enseignant.prenom or ""}'.strip()
                           if a.enseignant_id else ''),
            'dates': {'debut': a.date_debut.isoformat() if a.date_debut else None,
                      'fin': a.date_fin.isoformat() if a.date_fin else None},
            'statut': a.statut,
            'nb_seances_planifiees': (len(creneaux) * semaines) if creneaux else 0,
            'nb_seances_realisees': (nb_seances_realisees.get(a.groupe_id, 0)
                                     if a.groupe_id else 0),
            'planning': planning,
        })
    return Response({'total': len(lignes), 'resultats': lignes})
