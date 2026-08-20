"""Vérification rapide des endpoints EPT-INJS.

    cd backend && ./venv/bin/python ../eptinjs/backend/smoke_test.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'injs_lmd.settings.development')

import django  # noqa: E402

django.setup()

from rest_framework.test import APIClient  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.faculty.models import Teacher  # noqa: E402
from apps.students.models import Student  # noqa: E402
from eptinjs.models import PeriodeFormation, Seance  # noqa: E402

BASE = '/api/v1/eptinjs'


def verifier(client, methode, url, payload=None, *, resume=None):
    """Joue un appel et renvoie (ok, données)."""
    if methode == 'POST':
        reponse = client.post(url, payload or {}, format='json')
    else:
        reponse = client.get(url, format='json')
    ok = reponse.status_code < 400
    ligne = f'{"OK " if ok else "KO "} {reponse.status_code} {methode} {url}'
    if ok and resume:
        ligne += f' {resume(reponse.data)}'
    print(ligne)
    if not ok:
        print(f'      -> {str(reponse.data)[:300]}')
    return ok, reponse.data


def main():
    admin = User.objects.filter(is_superuser=True).first()
    if admin is None:
        print('Aucun super-utilisateur : lancez « manage.py seed_injs_demo ».')
        return 1

    client = APIClient()
    client.force_authenticate(user=admin)

    periode = PeriodeFormation.objects.first()
    seance = Seance.objects.filter(statut='planifiee').first()
    echecs = 0

    nombre = lambda item: f'count={item.get("count")}'  # noqa: E731

    lectures = [
        (f'{BASE}/periodes/', nombre),
        (f'{BASE}/periodes/{periode.id}/parametres/',
         lambda item: f'jours actifs {item["jours_actifs"]}, séances de {item["duree_seance_minutes"]} min'),
        (f'{BASE}/programmes/?periode={periode.id}', nombre),
        (f'{BASE}/seances/?page_size=5', nombre),
        (f'{BASE}/seances/grille/?periode={periode.id}',
         lambda item: f'{item["count"]} séances, {item["heures_totales"]} h, {len(item["jours"])} jour(s)'),
        (f'{BASE}/seances/conflits/?periode={periode.id}',
         lambda item: f'{item["count"]} anomalie(s) {item["par_type"] or ""}'),
        (f'{BASE}/seances/statistiques/',
         lambda item: (
             f'{item["seances"]["total"]} séances / {item["seances"]["heures"]} h, '
             f'présence {item["presences"]["taux_presence"]} %'
         )),
        (f'{BASE}/cours/?page_size=5',
         lambda item: f'{item["count"]} offres, couverture {item["kpis"]["taux_couverture"]} %'),
        (f'{BASE}/groupes/', nombre),
        (f'{BASE}/jours-feries/', nombre),
        (f'{BASE}/runs/', nombre),
    ]

    for url, resume in lectures:
        ok, _ = verifier(client, 'GET', url, resume=resume)
        echecs += 0 if ok else 1

    # Cycle de vie complet d'une séance : démarrage, émargement, QR, forçage, clôture.
    if seance is not None:
        for methode, url, payload, resume in [
            ('POST', f'{BASE}/seances/{seance.id}/demarrer/', {}, None),
            ('GET', f'{BASE}/seances/{seance.id}/emargement/', None,
             lambda item: f'{item["compteurs"]["attendus"]} attendu(s)'),
            ('GET', f'{BASE}/seances/{seance.id}/qr/', None,
             lambda item: f'image PNG de {len(item["qr_image_base64"])} o → {item["badge_url"]}'),
            ('POST', f'{BASE}/seances/{seance.id}/forcer-badgeage/', {'taux_min': 85, 'taux_max': 90},
             lambda item: f'{item["forces"]} forcé(s) à {item["taux_applique"]} %'),
            ('POST', f'{BASE}/seances/{seance.id}/terminer/', {},
             lambda item: f'{item["absents"]} absent(s), {item["sorties_automatiques"]} sortie(s) auto'),
        ]:
            ok, _ = verifier(client, methode, url, payload, resume=resume)
            echecs += 0 if ok else 1

    # Fiche Cours (ECUE) d'une offre réellement planifiée, toutes périodes confondues.
    planifiee = Seance.objects.exclude(statut='annulee').order_by('date').first()
    if planifiee is not None:
        offering_id = f'{planifiee.course_id}:{planifiee.promotion_id}'
        ok, _ = verifier(
            client, 'GET', f'{BASE}/cours/offering/?id={offering_id}',
            resume=lambda item: (
                f'\n      -> {item["course_code"]} · {item["promotion_name"]} · '
                f'{item["seances_count"]} séances sur {len(item["periodes"])} période(s), '
                f'{item["etudiants_count"]} étudiants, {item["enseignants_count"]} enseignant(s), '
                f'taux de présence {item["presences"]["taux_presence"]} %'
            ),
        )
        echecs += 0 if ok else 1

    # Badgeage QR de bout en bout : ouverture, scan entrée, scan sortie, clôture.
    a_badger = Seance.objects.filter(statut='planifiee').select_related('promotion').first()
    porteur = Student.objects.filter(
        promotion_id=a_badger.promotion_id, status='active',
    ).select_related('user').first() if a_badger else None

    if porteur is not None:
        print('    [badgeage QR bout en bout]')
        ok, ouverture = verifier(client, 'POST', f'{BASE}/seances/{a_badger.id}/demarrer/')
        echecs += 0 if ok else 1

        if ok:
            token = ouverture['qr']['token']
            scanneur = APIClient()
            scanneur.force_authenticate(user=porteur.user)
            for attendu in ('entree', 'sortie'):
                ok, resultat = verifier(
                    scanneur, 'POST', f'{BASE}/badge/scan/',
                    {'token': token, 'device_id': 'smoke-test'},
                    resume=lambda item: f'{item["sens"]} · {item["personne"]} · statut {item["statut"]}',
                )
                echecs += 0 if ok else 1
                if ok and resultat['sens'] != attendu:
                    print(f'      -> attendu « {attendu} », obtenu « {resultat["sens"]} »')
                    echecs += 1

            ok, _ = verifier(client, 'POST', f'{BASE}/seances/{a_badger.id}/terminer/')
            echecs += 0 if ok else 1

    # Emploi du temps personnel et badgeage, vus par un enseignant puis un étudiant.
    for libelle, profil in (
        ('enseignant', Teacher.objects.filter(seances__isnull=False).select_related('user').first()),
        ('étudiant', Student.objects.filter(status='active', promotion__seances__isnull=False).first()),
    ):
        if profil is None:
            print(f'—   aucun {libelle} rattaché à une séance, vues personnelles non testées')
            continue
        perso = APIClient()
        perso.force_authenticate(user=profil.user)
        print(f'    [{libelle} : {profil.user.get_full_name()}]')
        for url, resume in (
            (f'{BASE}/seances/mon-planning/', lambda item: f'{item["count"]} séances, {item["heures_totales"]} h'),
            (f'{BASE}/badge/statut/', lambda item: f'{len(item["seances"])} séance(s) ouverte(s)'),
            (f'{BASE}/badge/mon-historique/', lambda item: f'{item["count"]} pointage(s)'),
        ):
            ok, _ = verifier(perso, 'GET', url, resume=resume)
            echecs += 0 if ok else 1

    print(f'\n{"Tout est vert." if not echecs else f"{echecs} appel(s) en échec."}')
    return 1 if echecs else 0


if __name__ == '__main__':
    raise SystemExit(main())
