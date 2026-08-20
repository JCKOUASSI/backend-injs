"""Génère une maquette Master STAPS — Management du Sport (démo).

Crée UE / ECUE / liaisons ProgramCourse pour le programme M-STAPS (120 ECTS, S1–S4).
Les codes UE utilisent le préfixe MST9 pour éviter toute collision avec la maquette Licence.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.academics.models import (
    Course,
    Department,
    Institution,
    Program,
    ProgramCourse,
    Specialization,
    TeachingUnit,
)
from apps.academics.services.referentiels import bump_version

# (code_ue, nom_ue, semestre, crédits, [(code_ecue, nom, cm, td, tp), ...])
MAQUETTE_MASTER_MS = [
    # ── M1 — Semestre 1 (30 ECTS) ──────────────────────────────────────────
    (
        'MST9111',
        'STRATÉGIE ET GOUVERNANCE DES ORGANISATIONS SPORTIVES',
        1,
        6,
        [
            ('MST91111', 'Gouvernance des fédérations et clubs', 12, 18, 0),
            ('MST91112', 'Stratégie des organisations sportives', 12, 18, 0),
        ],
    ),
    (
        'MST9112',
        'DROIT DU SPORT AVANCÉ',
        1,
        4,
        [
            ('MST91121', 'Droit des associations et sociétés sportives', 10, 14, 0),
            ('MST91122', 'Contentieux et régulation du sport', 8, 12, 0),
        ],
    ),
    (
        'MST9113',
        'ÉCONOMIE ET FINANCEMENT DU SPORT',
        1,
        6,
        [
            ('MST91131', 'Économie du sport et modèles économiques', 12, 18, 0),
            ('MST91132', 'Financement et sponsoring sportif', 10, 16, 0),
        ],
    ),
    (
        'MST9114',
        'MARKETING SPORTIF STRATÉGIQUE',
        1,
        6,
        [
            ('MST91141', 'Marketing des produits et services sportifs', 12, 18, 0),
            ('MST91142', 'Marque, image et expérience spectateur', 10, 16, 0),
        ],
    ),
    (
        'MST9115',
        'MÉTHODOLOGIE DE LA RECHERCHE 1',
        1,
        4,
        [
            ('MST91151', 'Épistémologie et problématisation', 8, 14, 0),
            ('MST91152', 'Revue de littérature et outils documentaires', 6, 12, 0),
        ],
    ),
    (
        'MST9116',
        'ANGLAIS PROFESSIONNEL DU SPORT',
        1,
        4,
        [
            ('MST91161', 'Communication professionnelle en anglais', 6, 18, 0),
            ('MST91162', 'Anglais des organisations sportives', 6, 12, 0),
        ],
    ),
    # ── M1 — Semestre 2 (30 ECTS) ──────────────────────────────────────────
    (
        'MST9121',
        'MANAGEMENT DES ÉVÉNEMENTS SPORTIFS',
        2,
        6,
        [
            ('MST91211', 'Conception et production d’événements', 10, 20, 8),
            ('MST91212', 'Sécurité et logistique événementielle', 8, 16, 6),
        ],
    ),
    (
        'MST9122',
        'GESTION DES INFRASTRUCTURES ET ERP',
        2,
        5,
        [
            ('MST91221', 'Gestion des équipements sportifs', 10, 16, 0),
            ('MST91222', 'ERP et systèmes d’information sportifs', 8, 14, 6),
        ],
    ),
    (
        'MST9123',
        'COMMUNICATION ET MÉDIAS SPORTIFS',
        2,
        5,
        [
            ('MST91231', 'Relations presse et médias sportifs', 10, 14, 0),
            ('MST91232', 'Communication digitale des OS', 8, 16, 6),
        ],
    ),
    (
        'MST9124',
        'COMPTABILITÉ ET CONTRÔLE DE GESTION DES OS',
        2,
        6,
        [
            ('MST91241', 'Comptabilité des organisations sportives', 12, 18, 0),
            ('MST91242', 'Contrôle de gestion et tableaux de bord', 10, 16, 0),
        ],
    ),
    (
        'MST9125',
        'MÉTHODOLOGIE DE LA RECHERCHE 2',
        2,
        4,
        [
            ('MST91251', 'Méthodes qualitatives et quantitatives', 8, 14, 0),
            ('MST91252', 'Traitement de données et rédaction scientifique', 6, 12, 0),
        ],
    ),
    (
        'MST9126',
        'STAGE PROFESSIONNEL 1',
        2,
        4,
        [
            ('MST91261', 'Immersion professionnelle M1', 0, 10, 40),
        ],
    ),
    # ── M2 — Semestre 3 (30 ECTS) ──────────────────────────────────────────
    (
        'MST9131',
        'LEADERSHIP ET MANAGEMENT DES RH SPORTIVES',
        3,
        5,
        [
            ('MST91311', 'Leadership et conduite du changement', 10, 14, 0),
            ('MST91312', 'GRH des organisations sportives', 8, 16, 0),
        ],
    ),
    (
        'MST9132',
        'POLITIQUES PUBLIQUES DU SPORT',
        3,
        5,
        [
            ('MST91321', 'Politiques nationales et territoriales du sport', 10, 14, 0),
            ('MST91322', 'Partenariats public-privé et développement', 8, 14, 0),
        ],
    ),
    (
        'MST9133',
        'ENTREPRENEURIAT ET INNOVATION SPORTIVE',
        3,
        6,
        [
            ('MST91331', 'Création d’entreprise et business plan sport', 10, 18, 8),
            ('MST91332', 'Innovation et transformation digitale', 8, 14, 6),
        ],
    ),
    (
        'MST9134',
        'SÉMINAIRE DE PROFESSIONNALISATION',
        3,
        6,
        [
            ('MST91341', 'Séminaire métiers du management du sport', 6, 20, 10),
            ('MST91342', 'Études de cas et retours d’expérience', 4, 16, 8),
        ],
    ),
    (
        'MST9135',
        'ANALYSE DE DONNÉES ET AIDE À LA DÉCISION',
        3,
        4,
        [
            ('MST91351', 'Statistiques appliquées au management sportif', 8, 14, 6),
            ('MST91352', 'Outils décisionnels et indicateurs de performance', 6, 12, 4),
        ],
    ),
    (
        'MST9136',
        'STAGE PROFESSIONNEL 2',
        3,
        4,
        [
            ('MST91361', 'Immersion professionnelle M2', 0, 10, 40),
        ],
    ),
    # ── M2 — Semestre 4 (30 ECTS) ──────────────────────────────────────────
    (
        'MST9141',
        'MÉMOIRE DE RECHERCHE / PROJET PROFESSIONNEL',
        4,
        20,
        [
            ('MST91411', 'Mémoire de recherche ou projet professionnel', 4, 20, 80),
        ],
    ),
    (
        'MST9142',
        'SÉMINAIRE DE SOUTENANCE ET ÉTHIQUE',
        4,
        4,
        [
            ('MST91421', 'Éthique, déontologie et intégrité du sport', 8, 10, 0),
            ('MST91422', 'Préparation à la soutenance', 4, 12, 0),
        ],
    ),
    (
        'MST9143',
        'STAGE PROFESSIONNEL LONG',
        4,
        6,
        [
            ('MST91431', 'Stage d’immersion longue M2', 0, 8, 60),
        ],
    ),
]

MASTER_UE_PREFIX = 'MST9'
PROGRAM_CODE = 'M-STAPS'


class Command(BaseCommand):
    help = 'Génère la maquette démo Master STAPS — Management du Sport (M-STAPS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Remplace la maquette M-STAPS existante (UE MST9* + liaisons programme)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        inst, _ = Institution.objects.get_or_create(
            code='INJS',
            defaults={
                'name': 'Institut National de la Jeunesse et des Sports',
                'acronym': 'INJS',
                'city': 'Abidjan',
            },
        )
        dept, _ = Department.objects.get_or_create(
            institution=inst,
            code='STAPS',
            defaults={'name': 'Sciences et Techniques des Activités Physiques et Sportives'},
        )
        program, created = Program.objects.update_or_create(
            department=dept,
            code=PROGRAM_CODE,
            defaults={
                'name': 'Master STAPS - Management du Sport',
                'degree_type': 'M',
                'track': '',
                'duration_semesters': 4,
                'total_credits': 120,
                'description': 'Maquette démo Master Management du Sport (M1–M2)',
                'is_active': True,
            },
        )
        if created:
            self.stdout.write(f'Programme {PROGRAM_CODE} créé.')

        spec, _ = Specialization.objects.update_or_create(
            code='MS',
            defaults={
                'name': 'Management du Sport',
                'is_tronc_commun': False,
                'track': 'BOTH',
            },
        )

        if options['replace']:
            ProgramCourse.objects.filter(program=program).delete()
            Course.objects.filter(teaching_unit__code__startswith=MASTER_UE_PREFIX).delete()
            TeachingUnit.objects.filter(code__startswith=MASTER_UE_PREFIX).delete()
            self.stdout.write('Ancienne maquette Master MS supprimée.')
        elif ProgramCourse.objects.filter(program=program).exists():
            raise CommandError(
                f'{PROGRAM_CODE} possède déjà une maquette. '
                'Relancez avec --replace pour la régénérer.'
            )

        expected_credits = sum(item[3] for item in MAQUETTE_MASTER_MS)
        if expected_credits != 120:
            raise CommandError(f'Maquette incohérente : {expected_credits} ECTS au lieu de 120.')

        ue_count = ecue_count = link_count = 0
        for code, name, semester, credits, ecues in MAQUETTE_MASTER_MS:
            teaching_unit, _ = TeachingUnit.objects.update_or_create(
                code=code,
                defaults={
                    'name': name[:255],
                    'credits_ects': credits,
                    'semester_number': semester,
                    'department': dept,
                    'description': 'Maquette démo Master Management du Sport',
                },
            )
            ue_count += 1

            for ecue_code, ecue_name, hours_cm, hours_td, hours_tp in ecues:
                Course.objects.update_or_create(
                    teaching_unit=teaching_unit,
                    code=ecue_code,
                    defaults={
                        'name': ecue_name[:255],
                        'hours_cm': hours_cm,
                        'hours_td': hours_td,
                        'hours_tp': hours_tp,
                    },
                )
                ecue_count += 1

            ProgramCourse.objects.update_or_create(
                program=program,
                teaching_unit=teaching_unit,
                specialization=spec,
                defaults={
                    'semester_number': semester,
                    'is_mandatory': True,
                    'credits_override': None,
                },
            )
            link_count += 1

        bump_version()
        self.stdout.write(self.style.SUCCESS(
            f'Maquette Master MS : {ue_count} UE, {ecue_count} ECUE, '
            f'{link_count} liaisons → {PROGRAM_CODE} ({expected_credits} ECTS).'
        ))
